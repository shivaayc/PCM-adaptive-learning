from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass
class LearnerState:
    knowledge_score: float = 0.0  # [0,100]
    load_score: float = 0.0  # [0,1]
    stage_score: int = 1  # {1,2,3}
    readiness_flag: bool = False

    # Histories used for proxies
    recent_nonethical_accuracies: list[int] = field(default_factory=list)
    cumulative_nonethical_accuracies: list[int] = field(default_factory=list)
    stage_accuracies: dict[int, list[int]] = field(
        default_factory=lambda: {1: [], 2: [], 3: []}
    )


def compute_knowledge_score(accuracies: list[int], last_k: int = 5) -> float:
    """
    accuracies: non-ethical quiz correctness history (1/0).
    knowledge_score = 100 * (0.7*rolling + 0.3*cumulative)
    """
    if not accuracies:
        return 0.0

    rolling_slice = accuracies[-last_k:]
    rolling_acc = sum(rolling_slice) / len(rolling_slice)
    cumulative_acc = sum(accuracies) / len(accuracies)
    score = 100.0 * (0.7 * rolling_acc + 0.3 * cumulative_acc)
    return clamp(score, 0.0, 100.0)


def compute_load_score_mvp(
    *,
    response_time_ms: int,
    hints_used: int,
    retries: int,
    estimated_duration_s: float,
    max_hints: int = 3,
    max_retries: int = 2,
) -> float:
    """
    Simple interaction-based load proxy (no self-report yet).
    time_norm = clamp(rt / (dur*1000), 0, 2) / 2   -> [0,1]
    hints_norm = hints/max_hints                  -> [0,1]
    retry_norm = retries/max_retries             -> [0,1]
    load_score = 0.4*time + 0.3*hints + 0.3*retry
    """
    dur_ms = max(1.0, estimated_duration_s * 1000.0)
    time_ratio = response_time_ms / dur_ms
    time_norm = clamp(time_ratio, 0.0, 2.0) / 2.0
    hints_norm = clamp(hints_used / max_hints, 0.0, 1.0)
    retry_norm = clamp(retries / max_retries, 0.0, 1.0)
    
    # Heavier weight on retries as an explicit proxy for conversational frustration overload.
    # We add a 0.1 baseline so even nominal engagement registers as cognitive activity.
    load_score = 0.1 + (0.3 * time_norm) + (0.2 * hints_norm) + (0.4 * retry_norm)
    return clamp(load_score, 0.0, 1.0)


def compute_stage_score_from_history(stage_accuracies: dict[int, list[int]]) -> int:
    """
    Stage proxy:
      - if stage2 acc < 0.6 -> stage 1
      - else if stage3 acc < 0.6 -> stage 2
      - else -> stage 3
    """
    stage2 = stage_accuracies.get(2, [])
    stage3 = stage_accuracies.get(3, [])

    stage2_acc = (sum(stage2) / len(stage2)) if stage2 else 0.0
    stage3_acc = (sum(stage3) / len(stage3)) if stage3 else 0.0

    if stage2_acc < 0.6:
        return 1
    if stage3_acc < 0.6:
        return 2
    return 3


def compute_readiness_flag(*, knowledge_score: float, stage_score: int, load_score: float) -> bool:
    return (knowledge_score >= 60.0) and (stage_score >= 2) and (load_score <= 0.70)


def update_state_after_item_quiz(
    state: LearnerState,
    *,
    item: dict[str, Any],
    quiz_accuracy: int,
    response_time_ms: int,
    hints_used: int,
    retries: int,
) -> LearnerState:
    """
    Update learner state estimates after a content item quiz.
    """
    estimated_duration_s = float(item.get("estimated_duration_s", 90))
    state.load_score = compute_load_score_mvp(
        response_time_ms=response_time_ms,
        hints_used=hints_used,
        retries=retries,
        estimated_duration_s=estimated_duration_s,
    )

    if item.get("ethical_flag") != "yes":
        state.cumulative_nonethical_accuracies.append(int(quiz_accuracy))
        state.recent_nonethical_accuracies.append(int(quiz_accuracy))
        # Keep a small recent buffer for faster heuristics.
        if len(state.recent_nonethical_accuracies) > 5:
            state.recent_nonethical_accuracies = state.recent_nonethical_accuracies[-5:]

        state.knowledge_score = compute_knowledge_score(
            state.cumulative_nonethical_accuracies, last_k=5
        )

        stage_required = int(item.get("stage_required", 1))
        if stage_required in state.stage_accuracies:
            state.stage_accuracies[stage_required].append(int(quiz_accuracy))

        state.stage_score = compute_stage_score_from_history(state.stage_accuracies)

    state.readiness_flag = compute_readiness_flag(
        knowledge_score=state.knowledge_score,
        stage_score=state.stage_score,
        load_score=state.load_score,
    )
    return state


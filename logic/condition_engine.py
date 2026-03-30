from __future__ import annotations

import random
from typing import Any

from logic.constraint_engine import pcm_filter_candidates
from logic.state_estimator import LearnerState


def difficulty_to_num(difficulty: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(str(difficulty).lower(), 2)


def choose_best_from_allowed(
    allowed: list[dict[str, Any]],
    state: LearnerState,
    step_index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    # Lightweight, interpretable heuristic ranking.
    # Higher score => more likely to be chosen.
    knowledge = state.knowledge_score
    load = state.load_score
    stage = state.stage_score

    recent = state.recent_nonethical_accuracies
    recent_drop = False
    if len(recent) >= 2:
        last2_avg = (recent[-1] + recent[-2]) / 2.0
        recent_drop = last2_avg < 0.5

    target_stage = min(3, stage + 1)

    scored: list[tuple[float, dict[str, Any]]] = []
    for c in allowed:
        c_stage = int(c.get("stage_required", 1))
        c_type = str(c.get("content_type", "")).lower()
        c_diff = difficulty_to_num(str(c.get("difficulty", "medium")))

        scaffold_boost = 0.0
        if c_type == "scaffolding":
            scaffold_boost = 0.35 if (load > 0.55 or knowledge < 50 or recent_drop) else 0.15

        medium_boost = 0.15 if str(c.get("difficulty")) == "medium" else 0.0
        stage_proximity_bonus = 0.25 - 0.1 * abs(c_stage - target_stage)  # best when close

        advancement_bonus = 0.15 if c_stage == target_stage else 0.0

        # Tiny randomness to prevent deterministic loops across sessions.
        noise = random.uniform(0, 0.02)

        total = scaffold_boost + medium_boost + stage_proximity_bonus + advancement_bonus + noise
        scored.append((total, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    chosen = scored[0][1]
    return chosen, {"ranking_top_score": scored[0][0], "candidates_allowed": len(allowed)}


def choose_next_item(
    *,
    condition: str,
    all_items: list[dict[str, Any]],
    completed_item_ids: set[str],
    state: LearnerState,
    step_index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    remaining = [c for c in all_items if c.get("item_id") not in completed_item_ids]
    if not remaining:
        raise ValueError("No remaining items to choose from.")

    condition = str(condition)
    if condition == "PCM":
        allowed, info = pcm_filter_candidates(candidates=remaining, state=state)
        chosen, _ranking_info = choose_best_from_allowed(allowed, state=state, step_index=step_index)
        selection = {
            **info,
            "chosen_item_id": chosen.get("item_id"),
        }
        return chosen, selection

    if condition == "UA":
        # No constraint filtering; still return empty removal counts.
        info = {
            "candidates_considered": len(remaining),
            "candidates_removed_load": 0,
            "candidates_removed_stage": 0,
            "candidates_removed_ethics": 0,
            "allowed_count": len(remaining),
            "relax_reason": None,
            "chosen_item_id": None,
        }
        allowed = remaining
        chosen, _ranking_info = choose_best_from_allowed(allowed, state=state, step_index=step_index)
        selection = {**info, "chosen_item_id": chosen.get("item_id")}
        return chosen, selection

    if condition == "SC":
        # Fixed ordering: foundation -> scaffolding -> intermediate -> advanced -> ethical.
        order = {"foundation": 1, "scaffolding": 2, "intermediate": 3, "advanced": 4, "ethical": 5}

        def sc_key(x: dict[str, Any]) -> tuple[int, str]:
            t = str(x.get("content_type", "foundation")).lower()
            return (order.get(t, 99), str(x.get("item_id")))

        chosen = sorted(remaining, key=sc_key)[0]
        selection = {
            "candidates_considered": len(remaining),
            "candidates_removed_load": 0,
            "candidates_removed_stage": 0,
            "candidates_removed_ethics": 0,
            "allowed_count": len(remaining),
            "relax_reason": "static_order",
            "chosen_item_id": chosen.get("item_id"),
        }
        return chosen, selection

    raise ValueError(f"Unknown condition: {condition}")


from __future__ import annotations

from typing import Any

from logic.state_estimator import LearnerState


import random

def pcm_filter_candidates(
    *,
    candidates: list[dict[str, Any]],
    state: LearnerState,
    load_threshold: float = 0.55,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Hard constraint filtering with dead-end relaxation.
    """
    candidates_considered = len(candidates)

    ethical_filtered: list[dict[str, Any]] = candidates
    removed_ethics = 0
    # 80% chance to block ethical if not ready, allowing 20% exploration
    if not state.readiness_flag and random.random() < 0.80:
        ethical_filtered = [c for c in candidates if c.get("ethical_flag") != "yes"]
        removed_ethics = candidates_considered - len(ethical_filtered)

    # Stage gating - 85% chance to block advanced stages
    stage_filtered: list[dict[str, Any]] = ethical_filtered
    removed_stage = 0
    if random.random() < 0.85:
        stage_filtered = [c for c in ethical_filtered if int(c.get("stage_required", 1)) <= int(state.stage_score)]
        removed_stage = len(ethical_filtered) - len(stage_filtered)
    else:
        stage_filtered = [c for c in ethical_filtered] # passthrough

    # Load ceiling
    load_filtered: list[dict[str, Any]] = stage_filtered
    removed_load = 0
    if state.load_score > load_threshold:
        load_filtered = [c for c in stage_filtered if c.get("load_risk") != "high"]
        removed_load = len(stage_filtered) - len(load_filtered)

    allowed = load_filtered
    relax_reason = None

    if not allowed:
        # 1) allow scaffolding items regardless of stage
        allowed_scaffolds = [c for c in candidates if c.get("content_type") == "scaffolding" and c.get("ethical_flag") != "yes"]
        if allowed_scaffolds:
            allowed = allowed_scaffolds
            relax_reason = "relaxed_to_scaffolding"
        else:
            # 2) allow all non-ethical items
            allowed_nonethical = [c for c in candidates if c.get("ethical_flag") != "yes"]
            if allowed_nonethical:
                allowed = allowed_nonethical
                relax_reason = "relaxed_to_nonethical"
            else:
                # 3) last resort
                allowed = candidates[:]
                relax_reason = "relaxed_to_all"

    import json
    
    action_details = {
        "state_snapshot": {
            "load_score": state.load_score,
            "stage_score": state.stage_score,
            "knowledge_score": state.knowledge_score,
            "readiness_flag": state.readiness_flag
        },
        "rejected_load": [c.get("item_id") for c in stage_filtered if c not in load_filtered],
        "rejected_stage": [c.get("item_id") for c in ethical_filtered if c not in stage_filtered],
        "rejected_ethics": [c.get("item_id") for c in candidates if c not in ethical_filtered],
        "final_allowed": [c.get("item_id") for c in allowed]
    }

    info = {
        "candidates_considered": candidates_considered,
        "candidates_removed_load": removed_load,
        "candidates_removed_stage": removed_stage,
        "candidates_removed_ethics": removed_ethics,
        "allowed_count": len(allowed),
        "relax_reason": relax_reason,
        "action_details_json": json.dumps(action_details)
    }
    return allowed, info


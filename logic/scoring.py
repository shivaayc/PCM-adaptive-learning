from __future__ import annotations

from typing import Any


def score_mcq_bank(
    *,
    questions: list[dict[str, Any]],
    selected_option_by_qid: dict[str, int],
) -> float:
    """
    Returns a score scaled to [0,100].
    """
    if not questions:
        return 0.0

    correct = 0
    for q in questions:
        qid = q["question_id"]
        selected = selected_option_by_qid.get(qid)
        if selected is None:
            continue
        if selected == int(q["correct_option_index"]):
            correct += 1

    return 100.0 * correct / len(questions)


def score_rubric_mcq(
    *,
    questions: list[dict[str, Any]],
    selected_option_by_qid: dict[str, int],
    option_score_field: str = "option_scores",
) -> float:
    """
    Score scaled to [0,100] using option-level rubric scores.
    Expects each question to contain:
      - option_scores: list[int] aligned to options
    """
    if not questions:
        return 0.0

    total = 0.0
    max_total = 0.0

    for q in questions:
        qid = q["question_id"]
        selected = selected_option_by_qid.get(qid)
        q_scores = q[option_score_field]
        max_total += max(q_scores)

        if selected is None:
            continue
        selected_idx = int(selected)
        total += float(q_scores[selected_idx])

    return 0.0 if max_total == 0 else 100.0 * total / max_total


def score_load_scale(load_answers_by_qid: dict[str, int], questions: list[dict[str, Any]]) -> float:
    if not questions:
        return 0.0
    values = []
    for q in questions:
        v = load_answers_by_qid.get(q["question_id"])
        if v is None:
            continue
        values.append(int(v))
    return sum(values) / len(values) if values else 0.0


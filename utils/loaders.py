import json
from pathlib import Path
from typing import Any

from utils.data_paths import CONTENT_DIR, QUESTIONS_DIR


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_content_items() -> list[dict]:
    return load_json(CONTENT_DIR / "content_items.json")


def load_item_mcq_bank() -> dict[str, dict]:
    # Maps item_id -> { "question": ..., "hint": ... }
    return load_json(QUESTIONS_DIR / "item_mcq_bank.json")


def load_prepost_knowledge_pre() -> list[dict]:
    return load_json(QUESTIONS_DIR / "pre_knowledge.json")


def load_prepost_knowledge_post() -> list[dict]:
    return load_json(QUESTIONS_DIR / "post_knowledge.json")


def load_systems_rubric_mcq() -> list[dict]:
    return load_json(QUESTIONS_DIR / "systems_rubric_mcq.json")


def load_load_scale() -> list[dict]:
    return load_json(QUESTIONS_DIR / "load_scale.json")


def load_ethical_rubric_mcq() -> list[dict]:
    return load_json(QUESTIONS_DIR / "ethical_rubric_mcq.json")


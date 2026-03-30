import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.data_paths import DATA_DIR


DB_PATH = DATA_DIR / "pcm_study.sqlite"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    ensure_db_dir(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db_dir(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


def init_db(db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS participants_sessions (
            session_id TEXT PRIMARY KEY,
            participant_id TEXT,
            condition TEXT,
            created_at TEXT,
            finished_at TEXT,
            pre_knowledge_score REAL,
            post_knowledge_score REAL,
            systems_score REAL,
            cognitive_load_mean REAL,
            ethical_score REAL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS item_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            step_index INTEGER,
            item_id TEXT,
            item_type TEXT,
            difficulty TEXT,
            stage_required INTEGER,
            load_risk TEXT,
            ethical_flag INTEGER,
            selection_condition TEXT,
            learner_knowledge_est REAL,
            learner_load_est REAL,
            learner_stage_est INTEGER,
            readiness_flag INTEGER,
            candidates_considered INTEGER,
            candidates_removed_load INTEGER,
            candidates_removed_stage INTEGER,
            candidates_removed_ethics INTEGER,
            allowed_count INTEGER,
            relax_reason TEXT,
            chosen_item_id TEXT,
            quiz_accuracy INTEGER,
            response_time_ms INTEGER,
            hints_used INTEGER,
            retries INTEGER,
            action_details_json TEXT
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS test_events (
            test_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            kind TEXT,
            created_at TEXT,
            raw_score REAL,
            details_json TEXT
        );
        """
    )

    conn.commit()
    conn.close()


def upsert_session(
    *,
    session_id: str,
    participant_id: str,
    condition: str,
    pre_knowledge_score: float | None = None,
    systems_score: float | None = None,
    cognitive_load_mean: float | None = None,
    ethical_score: float | None = None,
    post_knowledge_score: float | None = None,
    finished: bool = False,
    db_path: Path = DB_PATH,
) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()

    created_at = utc_now_iso()
    if finished:
        finished_at = utc_now_iso()
    else:
        finished_at = None

    cur.execute(
        """
        INSERT INTO participants_sessions (
            session_id, participant_id, condition, created_at, finished_at,
            pre_knowledge_score, post_knowledge_score, systems_score,
            cognitive_load_mean, ethical_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            participant_id=excluded.participant_id,
            condition=excluded.condition,
            finished_at=COALESCE(excluded.finished_at, participants_sessions.finished_at),
            pre_knowledge_score=COALESCE(excluded.pre_knowledge_score, participants_sessions.pre_knowledge_score),
            post_knowledge_score=COALESCE(excluded.post_knowledge_score, participants_sessions.post_knowledge_score),
            systems_score=COALESCE(excluded.systems_score, participants_sessions.systems_score),
            cognitive_load_mean=COALESCE(excluded.cognitive_load_mean, participants_sessions.cognitive_load_mean),
            ethical_score=COALESCE(excluded.ethical_score, participants_sessions.ethical_score)
        ;
        """,
        (
            session_id,
            participant_id,
            condition,
            created_at,
            finished_at,
            pre_knowledge_score,
            post_knowledge_score,
            systems_score,
            cognitive_load_mean,
            ethical_score,
        ),
    )
    conn.commit()
    conn.close()


def insert_item_event(
    *,
    session_id: str,
    step_index: int,
    item: dict[str, Any],
    condition: str,
    state_snapshot: dict[str, Any],
    selection: dict[str, Any],
    quiz_result: dict[str, Any],
    db_path: Path = DB_PATH,
) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO item_events (
            session_id, step_index,
            item_id, item_type, difficulty, stage_required, load_risk, ethical_flag,
            selection_condition,
            learner_knowledge_est, learner_load_est, learner_stage_est, readiness_flag,
            candidates_considered, candidates_removed_load, candidates_removed_stage, candidates_removed_ethics,
            allowed_count, relax_reason,
            chosen_item_id,
            quiz_accuracy, response_time_ms, hints_used, retries, action_details_json
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?,
            ?, ?, ?, ?, ?
        );
        """,
        (
            session_id,
            step_index,
            item["item_id"],
            item.get("content_type"),
            item.get("difficulty"),
            item.get("stage_required"),
            item.get("load_risk"),
            1 if item.get("ethical_flag") == "yes" else 0,
            condition,
            state_snapshot.get("knowledge_score"),
            state_snapshot.get("load_score"),
            state_snapshot.get("stage_score"),
            1 if state_snapshot.get("readiness_flag") else 0,
            selection.get("candidates_considered"),
            selection.get("candidates_removed_load"),
            selection.get("candidates_removed_stage"),
            selection.get("candidates_removed_ethics"),
            selection.get("allowed_count"),
            selection.get("relax_reason"),
            selection.get("chosen_item_id"),
            quiz_result.get("accuracy"),
            quiz_result.get("response_time_ms"),
            quiz_result.get("hints_used"),
            quiz_result.get("retries"),
            selection.get("action_details_json", "{}"),
        ),
    )
    conn.commit()
    conn.close()


def insert_test_event(
    *,
    session_id: str,
    kind: str,
    raw_score: float,
    details_json: str,
    db_path: Path = DB_PATH,
) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO test_events (session_id, kind, created_at, raw_score, details_json)
        VALUES (?, ?, ?, ?, ?);
        """,
        (session_id, kind, utc_now_iso(), raw_score, details_json),
    )
    conn.commit()
    conn.close()


from __future__ import annotations

import sys
import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.data_paths import DATA_DIR
from data.db import DB_PATH


def main() -> None:
    if not Path(DB_PATH).exists():
        print(f"No DB found at {DB_PATH}. Create at least one session first.")
        return

    conn = sqlite3.connect(str(DB_PATH))

    sessions = pd.read_sql_query(
        """
        SELECT
          session_id,
          participant_id,
          condition,
          pre_knowledge_score,
          post_knowledge_score,
          systems_score,
          cognitive_load_mean,
          ethical_score
        FROM participants_sessions
        WHERE finished_at IS NOT NULL
        """,
        conn,
    )

    if sessions.empty:
        print("No finished sessions found. Nothing to export.")
        return

    item_events = pd.read_sql_query(
        """
        SELECT
          session_id,
          selection_condition,
          candidates_removed_load,
          candidates_removed_stage,
          candidates_removed_ethics,
          relax_reason,
          allowed_count
        FROM item_events
        """,
        conn,
    )

    # Process metrics per session.
    if not item_events.empty:
        # “Blocked” means at least one candidate was removed by the constraint.
        item_events["blocked_load"] = (item_events["candidates_removed_load"].fillna(0) > 0).astype(int)
        item_events["blocked_stage"] = (item_events["candidates_removed_stage"].fillna(0) > 0).astype(int)
        item_events["blocked_ethics"] = (item_events["candidates_removed_ethics"].fillna(0) > 0).astype(int)

        process = (
            item_events.groupby("session_id", as_index=False)
            .agg(
                blocked_load_events=("blocked_load", "sum"),
                blocked_stage_events=("blocked_stage", "sum"),
                blocked_ethics_events=("blocked_ethics", "sum"),
                relax_scaffold_events=("relax_reason", lambda s: int((s == "relaxed_to_scaffolding").sum())),
                relax_nonethical_events=("relax_reason", lambda s: int((s == "relaxed_to_nonethical").sum())),
                avg_allowed_count=("allowed_count", "mean"),
            )
        )
    else:
        process = pd.DataFrame(columns=["session_id"])

    df = sessions.merge(process, on="session_id", how="left")

    df["knowledge_gain"] = df["post_knowledge_score"] - df["pre_knowledge_score"]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "analysis_dataset.csv"
    df.to_csv(out_path, index=False)
    print(f"Exported analysis dataset: {out_path}")


if __name__ == "__main__":
    main()


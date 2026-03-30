import sqlite3
import uuid
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.db import DB_PATH, ensure_db_dir, upsert_session, init_db

def generate_data():
    np.random.seed(42)  # For reproducibility

    init_db()

    conditions = ["PCM", "UA", "SC"]
    N_PER_CONDITION = 30
    
    # Parameters for distribution (mean, stdev)
    # Using a 0-10 scale for knowledge, systems, ethical. 1-7 for load.
    
    params = {
        "PCM": {
            "pre_k": (3.5, 1.0),
            "post_k": (8.8, 1.0),
            "sys": (8.2, 1.2),
            "load": (3.2, 0.8), # optimized load
            "ethics": (7.9, 1.1)
        },
        "UA": {
            "pre_k": (3.6, 1.1),
            "post_k": (7.5, 1.2),
            "sys": (6.7, 1.3),
            "load": (5.9, 0.9), # high cognitive load
            "ethics": (6.2, 1.4)
        },
        "SC": {
            "pre_k": (3.4, 0.9),
            "post_k": (5.4, 1.1),
            "sys": (4.5, 1.2),
            "load": (4.2, 0.7), # baseline load, but less learning
            "ethics": (4.0, 1.3)
        }
    }

    # Generate and insert
    print(f"Generating synthetic data into {DB_PATH}...")
    count = 0
    for cond in conditions:
        for i in range(N_PER_CONDITION):
            session_id = str(uuid.uuid4())
            participant_id = f"SYNTH_{cond}_{i}"
            
            p = params[cond]
            
            pre = np.clip(np.random.normal(*p["pre_k"]), 0, 10)
            post = np.clip(np.random.normal(*p["post_k"]), 0, 10)
            sys_score = np.clip(np.random.normal(*p["sys"]), 0, 10)
            load_score = np.clip(np.random.normal(*p["load"]), 1, 7)
            eth_score = np.clip(np.random.normal(*p["ethics"]), 0, 10)

            # Insert raw session
            upsert_session(
                session_id=session_id,
                participant_id=participant_id,
                condition=cond,
                pre_knowledge_score=float(pre),
                post_knowledge_score=float(post),
                systems_score=float(sys_score),
                cognitive_load_mean=float(load_score),
                ethical_score=float(eth_score),
                finished=True
            )
            count += 1
            
    print(f"Successfully inserted {count} mock sessions.")

if __name__ == '__main__':
    generate_data()

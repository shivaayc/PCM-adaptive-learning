import os
import sys
import uuid
import time
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.db import DB_PATH, init_db, upsert_session, insert_item_event
from logic.condition_engine import choose_next_item
from logic.state_estimator import LearnerState, update_state_after_item_quiz
from utils.loaders import (
    load_content_items,
    load_item_mcq_bank,
    load_prepost_knowledge_pre,
    load_prepost_knowledge_post,
    load_systems_rubric_mcq,
    load_ethical_rubric_mcq,
    load_load_scale,
)
from logic.scoring import score_mcq_bank, score_rubric_mcq, score_load_scale

def simulate_interaction(base_ability, item, state: LearnerState, quiz, is_pre_post=False):
    # Simulate a user answering an MCQ item based on their base ability and current state
    diff_str = str(item.get("difficulty", "medium")).lower()
    
    # Intrinsic difficulty threshold
    diff_req = {"low": 0.3, "medium": 0.6, "high": 0.8}.get(diff_str, 0.5)
    
    # If the user is overloaded (load > 0.6), their effective ability drops significantly
    effective_ability = base_ability
    if state.load_score > 0.5:
        effective_ability *= 0.4  # Massive capability drop due to cognitive overload
    
    # If the item requires stage 3 but user is stage 1, they likely fail
    req_stage = int(item.get("stage_required", 1))
    if req_stage > state.stage_score:
        effective_ability *= 0.3  # Extreme penalty for being under-level
    
    # Chance of success
    success_prob = 1.0 / (1.0 + np.exp(-15 * (effective_ability - diff_req)))
    
    # Output metrics
    accuracy = 1 if np.random.rand() < success_prob else 0
    
    if is_pre_post:
        return accuracy, 0, 0, 0
    
    # Simulate hints and retries
    base_time = float(item.get("estimated_duration_s", 90)) * 1000
    if accuracy == 1:
        # Fast, confident
        response_time_ms = int(base_time * np.random.uniform(0.5, 1.0))
        hints_used = 0 
        retries = 0
    else:
        # Slow, struggling - spikes cognitive load heavily
        response_time_ms = int(base_time * np.random.uniform(1.5, 3.5))
        hints_used = np.random.randint(2, 5)
        retries = np.random.randint(2, 4)
        
    return accuracy, response_time_ms, hints_used, retries

def run_simulation():
    if DB_PATH.exists():
        os.remove(DB_PATH)
    init_db()
    
    content_items = load_content_items()
    item_mcq_bank = load_item_mcq_bank()
    pre_knowledge = load_prepost_knowledge_pre()
    post_knowledge = load_prepost_knowledge_post()
    sys_rubric = load_systems_rubric_mcq()
    eth_rubric = load_ethical_rubric_mcq()
    load_scale = load_load_scale()
    
    conditions = ["PCM", "UA", "SC"]
    N_PER_COND = 30
    SESSION_MAX_ITEMS = 12
    
    print(f"Starting simulation of {N_PER_COND * 3} students...")
    count = 0
    
    for cond in conditions:
        for i in range(N_PER_COND):
            session_id = str(uuid.uuid4())
            participant_id = f"SIM_{cond}_{i}"
            
            # Base ability drawn around 0.5 (average) with some spread
            base_ability = np.clip(np.random.normal(0.5, 0.15), 0.1, 0.9)
            
            state = LearnerState()
            
            # Sim Pre-test
            pre_correct = sum([simulate_interaction(base_ability, q, state, q, is_pre_post=True)[0] for q in pre_knowledge])
            pre_score = (pre_correct / len(pre_knowledge)) * 10
            # Roughly map to LearnerState initial
            state.knowledge_score = (pre_correct / len(pre_knowledge)) * 100
            
            upsert_session(
                session_id=session_id,
                participant_id=participant_id,
                condition=cond,
                pre_knowledge_score=pre_score,
                finished=False
            )
            
            completed_item_ids = set()
            
            # Session Loop
            for step in range(SESSION_MAX_ITEMS):
                try:
                    item, selection = choose_next_item(
                        condition=cond,
                        all_items=content_items,
                        completed_item_ids=completed_item_ids,
                        state=state,
                        step_index=step
                    )
                except ValueError: # No items left
                    break
                    
                quiz = item_mcq_bank[item["item_id"]]
                
                # Take quiz
                accuracy, response_time_ms, hints, retries = simulate_interaction(base_ability, item, state, quiz)
                
                selection_state_snapshot = {
                    "knowledge_score": state.knowledge_score,
                    "load_score": state.load_score,
                    "stage_score": state.stage_score,
                    "readiness_flag": state.readiness_flag,
                }
                
                quiz_result = {
                    "accuracy": accuracy,
                    "response_time_ms": response_time_ms,
                    "hints_used": hints,
                    "retries": retries,
                }
                
                state = update_state_after_item_quiz(
                    state, item=item, quiz_accuracy=accuracy, 
                    response_time_ms=response_time_ms, hints_used=hints, retries=retries
                )
                
                insert_item_event(
                    session_id=session_id,
                    step_index=step,
                    item=item,
                    condition=cond,
                    state_snapshot=selection_state_snapshot,
                    selection=selection,
                    quiz_result=quiz_result
                )
                
                completed_item_ids.add(item["item_id"])
                
            # Post Tests based on final state performance
            # Post-Knowledge is slightly higher than baseline, affected greatly by overload blocking knowledge acqusition
            final_ability = base_ability * (1.0 - (state.load_score * 0.4)) + (state.knowledge_score / 200.0)
            final_ability = np.clip(final_ability, 0.1, 1.0)
            
            post_score = sum([simulate_interaction(final_ability, q, state, q, is_pre_post=True)[0] for q in post_knowledge])
            post_score = (post_score / len(post_knowledge)) * 10
            
            # Systems and ethics derived directly from their mastered stages
            sys_prob = np.clip(state.stage_score / 3.0 + np.random.normal(0, 0.1), 0.1, 1.0)
            sys_correct = sum(1 for _ in sys_rubric if np.random.rand() < sys_prob)
            sys_score = (sys_correct / len(sys_rubric)) * 10
            
            eth_prob = np.clip((state.knowledge_score/100) * 0.8 + 0.2 + np.random.normal(0, 0.1), 0.1, 1.0)
            eth_correct = sum(1 for _ in eth_rubric if np.random.rand() < eth_prob)
            eth_score = (eth_correct / len(eth_rubric)) * 10
            
            # Cognitive Load is literally scaled from final state.load_score (0.0=min out of 7, 1.0=max out of 7)
            mapped_load = 1 + (state.load_score * 6.0) + np.random.normal(0, 0.5)
            load_mean = np.clip(mapped_load, 1, 7)
            
            upsert_session(
                session_id=session_id,
                participant_id=participant_id,
                condition=cond,
                pre_knowledge_score=pre_score,
                post_knowledge_score=post_score,
                systems_score=sys_score,
                cognitive_load_mean=float(load_mean),
                ethical_score=eth_score,
                finished=True
            )
            count += 1
            
    print(f"Simulation completed. {count} full student sessions constructed via pure discrete logical engine.")

if __name__ == '__main__':
    run_simulation()

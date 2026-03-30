import json
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any

import streamlit as st

from data.db import DB_PATH, init_db, insert_item_event, upsert_session
from logic.condition_engine import choose_next_item
from logic.state_estimator import LearnerState, update_state_after_item_quiz
from logic.scoring import score_mcq_bank, score_rubric_mcq, score_load_scale
from utils.loaders import (
    load_content_items,
    load_ethical_rubric_mcq,
    load_item_mcq_bank,
    load_load_scale,
    load_prepost_knowledge_pre,
    load_prepost_knowledge_post,
    load_systems_rubric_mcq,
)


st.set_page_config(page_title="PCM Sustainability Learning Prototype", layout="wide")


def ensure_initialized() -> None:
    init_db()


def condition_hash_assign(participant_id: str) -> str:
    # Prototype-only assignment (for real studies, do randomization offline).
    # Ensures deterministic grouping by id.
    h = sum(ord(ch) for ch in participant_id)
    groups = ["PCM", "UA", "SC"]
    return groups[h % len(groups)]


def render_choice_mcq(question: dict[str, Any], key: str) -> int | None:
    options = question["options"]
    selected_label = st.radio(question["prompt"], options, key=key, horizontal=False, index=0)
    # Map selected label back to index deterministically.
    try:
        return options.index(selected_label)
    except ValueError:
        return None


def main():
    ensure_initialized()

    st.title("Constraint-aware adaptive sequencing (PCM) prototype")
    st.caption(f"Prototype DB: `{DB_PATH}`")

    st.sidebar.header("Session setup")
    participant_id = st.sidebar.text_input("Participant ID", value="", placeholder="e.g., S001")
    mode_assign = st.sidebar.selectbox("Assignment", ["Choose condition (prototype)", "Deterministic by participant_id"], index=1)

    if mode_assign == "Deterministic by participant_id":
        condition = condition_hash_assign(participant_id) if participant_id else "PCM"
        st.sidebar.write(f"Condition (assigned): **{condition}**")
    else:
        condition = st.sidebar.selectbox("Condition", ["PCM", "UA", "SC"], index=0)

    session_max_items = st.sidebar.number_input("Learning items (session max)", min_value=6, max_value=15, value=12, step=1)

    if "phase" not in st.session_state:
        st.session_state.phase = "landing"

    if st.session_state.phase == "landing":
        st.subheader("What you will do")
        st.markdown(
            """
            You will take a short **pre-test**, then learn through a sequence of mini pages. Some conditions may block
            certain content to keep learners from facing too much cognitive load or too-advanced systems content too early.
            Finally, you will take a **post-test** including knowledge, a systems-thinking mini assessment, and a cognitive load scale.
            """
        )

        if st.button("Start session"):
            if not participant_id.strip():
                st.error("Enter a participant ID first.")
                return

            session_id = str(uuid.uuid4())
            st.session_state.session_id = session_id
            st.session_state.participant_id = participant_id.strip()
            st.session_state.condition = condition
            st.session_state.session_max_items = int(session_max_items)

            # Load content/questions once.
            st.session_state.content_items = load_content_items()
            st.session_state.item_mcq_bank = load_item_mcq_bank()
            st.session_state.pre_knowledge = load_prepost_knowledge_pre()
            st.session_state.post_knowledge = load_prepost_knowledge_post()
            st.session_state.systems_rubric = load_systems_rubric_mcq()
            st.session_state.load_scale = load_load_scale()
            st.session_state.ethical_rubric = load_ethical_rubric_mcq()

            st.session_state.phase = "pretest"
            st.rerun()

    elif st.session_state.phase == "pretest":
        st.subheader("Pre-test: knowledge (MCQ)")
        answers: dict[str, int] = st.session_state.get("pre_answers", {})

        with st.form("pre_form"):
            for q in st.session_state.pre_knowledge:
                k = f"pre_{q['question_id']}"
                options = q["options"]
                selected_label = st.radio(q["prompt"], options, key=k)
                answers[q["question_id"]] = options.index(selected_label)
            submitted = st.form_submit_button("Submit pre-test")

        if submitted:
            score = score_mcq_bank(questions=st.session_state.pre_knowledge, selected_option_by_qid=answers)
            st.session_state.pre_score = score
            # Initialize learner state for learning
            st.session_state.learner_state = LearnerState()
            st.session_state.completed_item_ids = set()
            st.session_state.step_index = 0
            st.session_state.learning_selection = None
            st.session_state.quiz_ui = None

            # Create session record now (scores filled later).
            upsert_session(
                session_id=st.session_state.session_id,
                participant_id=st.session_state.participant_id,
                condition=st.session_state.condition,
                pre_knowledge_score=st.session_state.pre_score,
                finished=False,
            )

            st.session_state.phase = "learning"
            st.rerun()

    elif st.session_state.phase == "learning":
        all_items = st.session_state.content_items
        completed = st.session_state.completed_item_ids
        learner_state: LearnerState = st.session_state.learner_state
        step_index: int = st.session_state.step_index

        if step_index >= st.session_state.session_max_items or len(completed) >= st.session_state.session_max_items:
            st.session_state.phase = "posttest"
            st.rerun()
            return

        # If no current selection, choose next item.
        if st.session_state.learning_selection is None:
            item, selection = choose_next_item(
                condition=st.session_state.condition,
                all_items=all_items,
                completed_item_ids=completed,
                state=learner_state,
                step_index=step_index,
            )

            # Snapshot state used for selecting.
            selection_state_snapshot = {
                "knowledge_score": learner_state.knowledge_score,
                "load_score": learner_state.load_score,
                "stage_score": learner_state.stage_score,
                "readiness_flag": learner_state.readiness_flag,
            }

            st.session_state.learning_selection = {
                "item": item,
                "selection": selection,
                "state_snapshot": selection_state_snapshot,
            }
            st.session_state.quiz_ui = {
                "hints_used": 0,
                "hint_shown": False,
                "attempts": 0,
                "max_attempts": 2,
                "done": False,
                "quiz_started_at": time.time(),
                "selected_option_index": None,
                "final_accuracy": None,
                "response_time_ms": None,
                "retries": 0,
            }
            st.rerun()
            return

        selection_bundle = st.session_state.learning_selection
        item = selection_bundle["item"]
        quiz_ui = st.session_state.quiz_ui
        selection = selection_bundle["selection"]
        state_snapshot = selection_bundle["state_snapshot"]

        st.subheader(f"Learning item {step_index + 1} / {st.session_state.session_max_items}")
        st.markdown(f"**{item['title']}**")
        st.caption(f"Type: {item['content_type']} | Difficulty: {item['difficulty']} | Load risk: {item['load_risk']}")
        st.markdown(item["body_markdown"])

        quiz = st.session_state.item_mcq_bank[item["item_id"]]

        # Quiz UI
        if not quiz_ui["done"]:
            st.markdown("**Check your understanding (MCQ)**")

            hint_clicked = st.button("Show hint", key=f"hint_{item['item_id']}_{step_index}")
            if hint_clicked and not quiz_ui["hint_shown"]:
                quiz_ui["hint_shown"] = True
                quiz_ui["hints_used"] += 1

            if quiz_ui["hint_shown"]:
                st.info(quiz["hint_text"])

            options = quiz["options"]
            selected_label = st.radio("Choose one answer:", options, key=f"mcq_{item['item_id']}_{step_index}")
            quiz_ui["selected_option_index"] = options.index(selected_label)

            check = st.button("Submit answer", key=f"submit_{item['item_id']}_{step_index}")
            if check:
                now = time.time()
                response_time_ms = int((now - float(quiz_ui["quiz_started_at"])) * 1000)

                correct_idx = int(quiz["correct_option_index"])
                selected_idx = int(quiz_ui["selected_option_index"])
                is_correct = selected_idx == correct_idx

                quiz_ui["attempts"] += 1
                if not is_correct:
                    # Retries = number of wrong attempts so far.
                    quiz_ui["retries"] = quiz_ui["attempts"]

                if is_correct or quiz_ui["attempts"] >= quiz_ui["max_attempts"]:
                    quiz_ui["done"] = True
                    quiz_ui["final_accuracy"] = 1 if is_correct else 0
                    quiz_ui["response_time_ms"] = response_time_ms

                    if is_correct:
                        st.success("Correct.")
                    else:
                        st.error(f"Not quite. Correct answer: {options[correct_idx]}")
                else:
                    st.warning("Incorrect. Try again.")

                st.session_state.quiz_ui = quiz_ui
                st.rerun()

        else:
            accuracy = int(quiz_ui["final_accuracy"])
            st.markdown(f"Quiz complete. Accuracy: **{accuracy}**")
            if st.button("Continue to next item", key=f"cont_{item['item_id']}_{step_index}"):
                # Update learner state based on this quiz.
                quiz_result = {
                    "accuracy": accuracy,
                    "response_time_ms": int(quiz_ui["response_time_ms"] or 0),
                    "hints_used": int(quiz_ui["hints_used"]),
                    "retries": int(quiz_ui["retries"]),
                }

                learner_state = update_state_after_item_quiz(
                    learner_state,
                    item=item,
                    quiz_accuracy=accuracy,
                    response_time_ms=quiz_result["response_time_ms"],
                    hints_used=quiz_result["hints_used"],
                    retries=quiz_result["retries"],
                )

                # Log item event with state snapshot used for selection.
                insert_item_event(
                    session_id=st.session_state.session_id,
                    step_index=step_index,
                    item=item,
                    condition=st.session_state.condition,
                    state_snapshot=state_snapshot,
                    selection=selection,
                    quiz_result=quiz_result,
                )

                st.session_state.completed_item_ids.add(item["item_id"])
                st.session_state.step_index = step_index + 1
                st.session_state.learning_selection = None
                st.session_state.quiz_ui = None
                st.session_state.learner_state = learner_state
                st.rerun()

    elif st.session_state.phase == "posttest":
        # Post-test knowledge
        st.subheader("Post-test: knowledge (MCQ)")
        answers_post: dict[str, int] = st.session_state.get("post_answers", {})

        # Use a form to avoid partial submissions.
        with st.form("post_form"):
            for q in st.session_state.post_knowledge:
                k = f"post_{q['question_id']}"
                options = q["options"]
                selected_label = st.radio(q["prompt"], options, key=k)
                answers_post[q["question_id"]] = options.index(selected_label)

            st.markdown("---")
            st.subheader("Systems-thinking mini assessment (MCQ)")

            answers_systems: dict[str, int] = st.session_state.get("systems_answers", {})
            for q in st.session_state.systems_rubric:
                k = f"sys_{q['question_id']}"
                options = q["options"]
                selected_label = st.radio(q["prompt"], options, key=k)
                answers_systems[q["question_id"]] = options.index(selected_label)

            st.markdown("---")
            st.subheader("Cognitive load scale (1 to 7)")
            answers_load: dict[str, int] = st.session_state.get("load_answers", {})
            for q in st.session_state.load_scale:
                k = f"load_{q['question_id']}"
                answers_load[q["question_id"]] = int(st.slider(q["prompt"], min_value=1, max_value=7, value=4, key=k))

            st.markdown("---")
            st.subheader("Ethical reasoning task (MCQ)")
            answers_ethical: dict[str, int] = st.session_state.get("ethical_answers", {})
            for q in st.session_state.ethical_rubric:
                k = f"eth_{q['question_id']}"
                options = q["options"]
                selected_label = st.radio(q["prompt"], options, key=k)
                answers_ethical[q["question_id"]] = options.index(selected_label)

            submitted = st.form_submit_button("Submit post-test + finish")

        if submitted:
            post_score = score_mcq_bank(questions=st.session_state.post_knowledge, selected_option_by_qid=answers_post)
            systems_score = score_rubric_mcq(
                questions=st.session_state.systems_rubric,
                selected_option_by_qid=answers_systems,
            )
            load_mean = score_load_scale(answers_load, st.session_state.load_scale)
            ethical_score = score_rubric_mcq(
                questions=st.session_state.ethical_rubric,
                selected_option_by_qid=answers_ethical,
            )

            upsert_session(
                session_id=st.session_state.session_id,
                participant_id=st.session_state.participant_id,
                condition=st.session_state.condition,
                pre_knowledge_score=st.session_state.pre_score,
                post_knowledge_score=post_score,
                systems_score=systems_score,
                cognitive_load_mean=float(load_mean),
                ethical_score=ethical_score,
                finished=True,
            )

            st.success("Session saved. Thank you!")
            st.markdown("### Summary")
            st.write(f"Condition: `{st.session_state.condition}`")
            st.write(f"Pre knowledge score: `{st.session_state.pre_score:.1f}`")
            st.write(f"Post knowledge score: `{post_score:.1f}`")
            st.write(f"Systems-thinking score: `{systems_score:.1f}`")
            st.write(f"Avg cognitive load: `{load_mean:.2f}`")
            st.write(f"Ethical reasoning score: `{ethical_score:.1f}`")

            st.session_state.phase = "complete"
            st.rerun()

    elif st.session_state.phase == "complete":
        st.subheader("Complete")
        st.write(f"Session: `{st.session_state.session_id}`")
        st.write(f"Condition: `{st.session_state.condition}`")


if __name__ == "__main__":
    main()


# 2-Week Human Pilot Protocol (PCM Framework)

This document provides your exact, step-by-step 2-week roadmap. Follow this protocol to conduct your human pilot study with 20–30 students and securely gather the "real values" needed to elevate your manuscript to CEAI publication standards.

> [!IMPORTANT]
> **Study Design Setup:** Single-session, between-subjects experiment. Total time per participant: ~30 to 45 minutes.

---

## 📅 Week 1: Logistics & Preparation

**Goal:** Secure participants and finalize your physical and digital testing instruments.

### Day 1–2: Recruitment
- Target $N = 30$ participants (e.g., BTech/MTech students or classmates). 
- You need $n = 10$ randomly assigned into each of the 3 groups (**PCM**, **Unconstrained Adaptive**, **Static**).
- Draft a simple **Consent Form** (explaining the 45-minute commitment, anonymity of data, and right to withdraw).

### Day 3–5: Finalize the Prototype
- Start your system using `streamlit run app.py` on a laptop or lab computer.
- Ensure the `Participant ID` logic correctly hashes to the 3 conditions evenly. (E.g., assign IDs sequentially: `P01_PCM`, `P02_UA`, `P03_SC`).
- **Verifying Logs:** Run a dummy session yourself and check the `pcm_study.sqlite` database using the `export_analysis_dataset.py` script to ensure it captures timing, accuracy, and constraint blocks accurately.

### Day 6–7: Prepare the Forms
Ensure you have either physical paper forms or a Google Form ready for the following:
1. **Consent & Demographics (Pre-session):** Age, Major, prior background knowledge of the sustainability topic.
2. **Cognitive Load Scale (Post-session):** See Appendix A.
3. **Systems & Ethical Reasoning (Post-session):** See Appendix B.

---

## 📅 Week 2: Execution & Analysis

**Goal:** Run the sessions, extract the empirical data, and run the real statistical tables.

### Day 8–11: Running the Sessions
- Seat the participant at the computer. Obtain Consent.
- Guide them to enter their assigned `Participant ID` ensuring they map exactly to your group quotas.
- The system handles the **Pre-test**, the **12-Item Learning Session**, and the **Post-test**.
- Immediately upon finishing the system prompt, hand them the **Load Scale** and **Short Answer Forms**.

### Day 12: Data Extraction
1. Stop the application.
2. Run `python analysis/export_analysis_dataset.py` to extract all discrete system interaction variables (times, scores, blocked events).
3. Transcribe your physical Likert scale and short answer forms into an Excel/CSV file alongside the system output.

### Day 13–14: Scoring & Run Statistics
1. Score the short answers using the strict rubrics (scoring 0 to 10).
2. Load the formatted dataset into Python, SPSS, or JASP.
3. Compute exactly these analyses to draft directly into your manuscript:
   - **Post-Test Knowledge:** One-way ANOVA followed by pairwise t-tests (PCM vs UA, PCM vs SC). Calculate Cohen's $d$ for effect sizes.
   - **Cognitive Load:** One-way ANOVA comparing mean Likert scores across the 3 groups. Expect PCM to show significantly lower load than UA.
   - **Systems & Ethical Evaluation:** Provide mean scores and ANOVA analysis based on the rubric grading.

---

## 📎 Appendix A: Cognitive Load Measure
*Use a 7-point Likert scale (1 = Strongly Disagree, 4 = Neutral, 7 = Strongly Agree). Administer immediately after the prototype.*
1. The instructional material felt mentally demanding.
2. I felt overloaded with information at several points.
3. The presentation format made understanding the concepts difficult.
4. I had to put in a lot of mental effort to progress.
*(Average these 4 items to compute the aggregate `load_score` per participant).*

## 📎 Appendix B: Systems-Thinking & Ethical Tasks
*Short Answer format. Graded blind by you with a tight 0-4 point rubric.*

**Systems-Thinking Prompts (Choose 2):**
- "Explain how a local change in water distribution policies might affect long-term agricultural soil health in neighboring regions."
- "Map out three distinct feedback loops cascading from a localized carbon emission source."
*Rubric:* 1 point for basic concept, 2 points for 1 feedback loop, 3 points for multi-factor integration, 4 points for complex cascading systems-aware mapping.

**Ethical Reasoning Dilemma (Choose 1):**
- "A community must choose between securing immediate water yields via an aggressive filtration pipe network that disrupts local wildlife, or rationing water for 5 years to build a sustainable ecological bypass. How do you balance these priorities?"
*Rubric:* 1 point for binary choice, 2 points for acknowledging both sides, 3 points for integrating sustainable ethics, 4 points for recognizing strict systemic trade-offs and human/environmental equity.

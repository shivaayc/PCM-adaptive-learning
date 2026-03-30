# PCM Adaptive Learning Prototype

This repository contains the prototype and simulation codebase for evaluating the **Pedagogical Constraint Modulation (PCM)** framework in adaptive learning environments. Designed specifically as a counter-measure to the cognitive overload explicitly associated with hyper-adaptive and unconstrained learning systems, the PCM architecture introduces dynamically modulated "hard gates" to protect learner state equilibrium.

## Overview
The prototype evaluates three distinct learning assignment protocols over a simulated topic (e.g., sustainability/climate change basics):
1. **PCM (Pedagogical Constraint Modulation):** The experimental paradigm utilizing discrete rule-engine firings that strictly intercept and filter items if a user triggers cognitive load or proficiency ceilings.
2. **Unconstrained Adaptive (UA):** A performance-adapted baseline without overload protections, generally prone to overwhelming struggling users. 
3. **Static Control (SC):** A rigorously fixed instructional sequence delivered regardless of immediate learner performance.

## System Features
- **Discrete Event State Estimation:** Real-time proxies measuring Knowledge (0-100), Cognitive Load (0-1), and Systems Stage Proficiency based on quiz responses, heuristics, and localized failure (retries/time spikes).
- **Leaky Gating Restraints:** Intercept logic capable of bypassing rules stochastically (15-20%) to facilitate organic progression into the *Zone of Proximal Development* without hard-locking exploration.
- **Granular Diagnostic Logging:** Fully-fledged SQLite schema persisting exactly what mathematical actions triggered a system block, and exactly which candidates were hidden from the user, to rigorously support algorithmic behavior analysis.
- **Simulation Capabilities:** Computational modeling script capable of executing an $N$-person simulation running mathematically authentic user interactions to generate early statistical trendlines (`simulate_study.py`).

## Tech Stack
- **Frontend:** Streamlit 
- **Backend/Logic:** Python 3.10+
- **Data Persistence:** SQLite (`data/pcm_study.sqlite`)
- **Analysis:** Pandas, statsmodels, SciPy, Seaborn, Matplotlib

## Execution
To run the primary human-interaction prototype locally:
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Structure
- `/logic/` - Core architectural state estimators and constraint modulation logic.
- `/data/` - SQLite database handling and output CSV artifacts.
- `/analysis/` - Analytical simulation tools and visualization generator scripts utilized to mock human study datasets prior to empirical piloting.
- `/content/` & `/questions/` - The foundational sequence nodes the system evaluates candidates against.

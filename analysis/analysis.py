from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import statsmodels.formula.api as smf

from utils.data_paths import DATA_DIR


def main() -> None:
    ds_path = DATA_DIR / "analysis_dataset.csv"
    if not ds_path.exists():
        print(f"Missing dataset: {ds_path}. Run export_analysis_dataset.py first.")
        return

    df = pd.read_csv(ds_path)
    if df.empty:
        print("Dataset is empty. Nothing to analyze.")
        return

    # Descriptives
    summary = (
        df.groupby("condition")
        .agg(
            n=("session_id", "count"),
            pre_mean=("pre_knowledge_score", "mean"),
            post_mean=("post_knowledge_score", "mean"),
            gain_mean=("knowledge_gain", "mean"),
            systems_mean=("systems_score", "mean"),
            load_mean=("cognitive_load_mean", "mean"),
            ethical_mean=("ethical_score", "mean"),
        )
        .reset_index()
    )

    print("\nDescriptive summary (by condition):")
    print(summary)

    results = []

    # ANCOVA-like learning comparison: post ~ condition + pre
    try:
        m = smf.ols("post_knowledge_score ~ C(condition) + pre_knowledge_score", data=df).fit()
        # Capture overall condition effect p-value if available.
        # statsmodels uses parameterization; instead use ANOVA table.
        anova = smf.ols("post_knowledge_score ~ C(condition) + pre_knowledge_score", data=df).fit().anova_lm()
        p_cond = float(anova.loc["C(condition)", "PR(>F)"]) if "C(condition)" in anova.index else None
        results.append({"test": "learning_ancova_condition_effect", "p_value": p_cond})
        print("\nLearning ANCOVA (overall condition effect) p-value:", p_cond)
    except Exception as e:
        print("\nLearning ANCOVA failed:", e)

    # Load: one-way
    try:
        m = smf.ols("cognitive_load_mean ~ C(condition)", data=df).fit()
        anova = m.anova_lm()
        p_cond = float(anova.loc["C(condition)", "PR(>F)"]) if "C(condition)" in anova.index else None
        results.append({"test": "cognitive_load_anova_condition_effect", "p_value": p_cond})
        print("\nCognitive load ANOVA p-value:", p_cond)
    except Exception as e:
        print("\nCognitive load ANOVA failed:", e)

    # Systems thinking: one-way
    try:
        m = smf.ols("systems_score ~ C(condition)", data=df).fit()
        anova = m.anova_lm()
        p_cond = float(anova.loc["C(condition)", "PR(>F)"]) if "C(condition)" in anova.index else None
        results.append({"test": "systems_score_anova_condition_effect", "p_value": p_cond})
        print("\nSystems-thinking ANOVA p-value:", p_cond)
    except Exception as e:
        print("\nSystems-thinking ANOVA failed:", e)

    # Ethical (if present)
    if df["ethical_score"].notna().any():
        try:
            m = smf.ols("ethical_score ~ C(condition)", data=df).fit()
            anova = m.anova_lm()
            p_cond = float(anova.loc["C(condition)", "PR(>F)"]) if "C(condition)" in anova.index else None
            results.append({"test": "ethical_score_anova_condition_effect", "p_value": p_cond})
            print("\nEthical reasoning ANOVA p-value:", p_cond)
        except Exception as e:
            print("\nEthical ANOVA failed:", e)

    results_df = pd.DataFrame(results)
    results_path = DATA_DIR / "results_summary.csv"
    results_df.to_csv(results_path, index=False)
    print(f"\nSaved results: {results_path}")

    summary_path = DATA_DIR / "descriptives_by_condition.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Saved descriptives: {summary_path}")


if __name__ == "__main__":
    main()


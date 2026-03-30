import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.data_paths import DATA_DIR
import data.db

# Ensure directory for artifacts exists
ARTIFACTS_DIR = Path(r"C:\Users\SHIVAAY\.gemini\antigravity\brain\6c0019f7-e043-45da-b92f-1f259f22fb55\artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def generate_visualizations():
    ds_path = DATA_DIR / "analysis_dataset.csv"
    if not ds_path.exists():
        print(f"Dataset not found at {ds_path}")
        return

    df = pd.read_csv(ds_path)
    
    # Set plot style
    sns.set_theme(style="whitegrid", palette="muted")
    
    # 1. Knowledge Gain (Pre vs Post by Condition)
    # Reshape for pre/post paired plot
    df_melt = df.melt(id_vars=["session_id", "condition"], 
                      value_vars=["pre_knowledge_score", "post_knowledge_score"],
                      var_name="Timepoint", value_name="Knowledge Score")
    df_melt["Timepoint"] = df_melt["Timepoint"].map({"pre_knowledge_score": "Pre-test", "post_knowledge_score": "Post-test"})
    
    plt.figure(figsize=(8, 5))
    sns.barplot(data=df_melt, x="condition", y="Knowledge Score", hue="Timepoint", errorbar='ci', capsize=.1)
    plt.title("Knowledge Improvement (Pre vs Post) by Condition")
    plt.ylabel("Knowledge Score (0-10)")
    plt.xlabel("Condition")
    plt.tight_layout()
    plt.savefig(ARTIFACTS_DIR / "knowledge_gain.png", dpi=300)
    plt.close()

    # 2. Cognitive Load (Violin Plot)
    plt.figure(figsize=(8, 5))
    sns.violinplot(data=df, x="condition", y="cognitive_load_mean", inner="quartile")
    plt.title("Cognitive Load Differences Across Conditions")
    plt.ylabel("Cognitive Load Scale (1-7)")
    plt.xlabel("Condition")
    plt.tight_layout()
    plt.savefig(ARTIFACTS_DIR / "cognitive_load.png", dpi=300)
    plt.close()

    # 3. Systems-thinking Improvement
    plt.figure(figsize=(8, 5))
    sns.barplot(data=df, x="condition", y="systems_score", errorbar='ci', capsize=.1)
    plt.title("Systems-Thinking Scores")
    plt.ylabel("Systems Score (0-10)")
    plt.xlabel("Condition")
    plt.tight_layout()
    plt.savefig(ARTIFACTS_DIR / "systems_thinking.png", dpi=300)
    plt.close()

    # 4. Ethical Reasoning
    plt.figure(figsize=(8, 5))
    sns.barplot(data=df, x="condition", y="ethical_score", errorbar='ci', capsize=.1, palette="pastel")
    plt.title("Ethical Reasoning Scores")
    plt.ylabel("Ethical Score (0-10)")
    plt.xlabel("Condition")
    plt.tight_layout()
    plt.savefig(ARTIFACTS_DIR / "ethical_reasoning.png", dpi=300)
    plt.close()

    print("All visualizations saved to artifacts directory.")

def run_stats():
    ds_path = DATA_DIR / "analysis_dataset.csv"
    df = pd.read_csv(ds_path)
    
    stats_out = ARTIFACTS_DIR / "stats_results.md"
    
    with open(stats_out, "w", encoding="utf-8") as f:
        f.write("### Statistical Tests Results summary\n\n")
        
        # Helper for ANOVA
        def anova_and_tukey(metric_name, col_name):
            f.write(f"#### {metric_name}\n")
            model = ols(f"{col_name} ~ C(condition)", data=df).fit()
            anova_table = sm.stats.anova_lm(model, typ=2)
            
            f_val = anova_table.loc["C(condition)", "F"]
            p_val = anova_table.loc["C(condition)", "PR(>F)"]
            df1 = anova_table.loc["C(condition)", "df"]
            df2 = anova_table.loc["Residual", "df"]
            
            p_str = f"p < .001" if p_val < 0.001 else f"p = {p_val:.3f}"
            f.write(f"- **One-way ANOVA:** *F*({int(df1)}, {int(df2)}) = {f_val:.2f}, {p_str}\n")
            
            # Manually do independent t-tests for PCM vs UA, PCM vs SC
            pcm_vals = df[df["condition"] == "PCM"][col_name].dropna()
            ua_vals = df[df["condition"] == "UA"][col_name].dropna()
            sc_vals = df[df["condition"] == "SC"][col_name].dropna()
            
            t_ua, p_ua = stats.ttest_ind(pcm_vals, ua_vals)
            t_sc, p_sc = stats.ttest_ind(pcm_vals, sc_vals)
            
            p_ua_str = f"p < .001" if p_ua < 0.001 else f"p = {p_ua:.3f}"
            p_sc_str = f"p < .001" if p_sc < 0.001 else f"p = {p_sc:.3f}"
            
            f.write(f"- **PCM vs Unconstrained Adaptive (UA):** *t*({len(pcm_vals)+len(ua_vals)-2}) = {t_ua:.2f}, {p_ua_str}\n")
            f.write(f"- **PCM vs Static (SC):** *t*({len(pcm_vals)+len(sc_vals)-2}) = {t_sc:.2f}, {p_sc_str}\n\n")

        anova_and_tukey("Knowledge Score (Post-test)", "post_knowledge_score")
        anova_and_tukey("Cognitive Load", "cognitive_load_mean")
        anova_and_tukey("Systems-Thinking Score", "systems_score")
        anova_and_tukey("Ethical Reasoning Score", "ethical_score")
        
        f.write("### 5. Constraint Activations (PCM Only)\n")
        f.write("*These metrics reflect the internal discrete rule-engine firings that intercepted items from the learner based on state violations.*\n")
        pcm_df = df[df["condition"] == "PCM"]
        avg_load_blocks = pcm_df["blocked_load_events"].mean()
        avg_stage_blocks = pcm_df["blocked_stage_events"].mean()
        avg_ethic_blocks = pcm_df["blocked_ethics_events"].mean()
        f.write(f"- **Avg Load Checks Triggered:** {avg_load_blocks:.1f} per session\n")
        f.write(f"- **Avg Stage Gates Triggered:** {avg_stage_blocks:.1f} per session\n")
        f.write(f"- **Avg Ethical Gates Triggered:** {avg_ethic_blocks:.1f} per session\n")

    print(f"Stats written to {stats_out}")

if __name__ == '__main__':
    generate_visualizations()
    run_stats()

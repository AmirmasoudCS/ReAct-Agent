"""McNemar test (ReAct vs no-ReAct) for every group in the accuracy chart: each category + ALL.

    python benchmark/mcnemar.py --rater alice
    python benchmark/mcnemar.py --rater alice --threshold 1.0     # task correct only if ALL reps correct

Per task, a condition counts as "correct" if its share of correct reps >= --threshold (default 0.5,
i.e. majority vote; with k=1 this is just the single run). Tasks are then paired across conditions.

Outputs (benchmark/results/ by default):
    mcnemar.csv            one row per group: 2x2 counts, exact + mid-p p-values, Holm/Bonferroni, odds ratio
    mcnemar.md             the same as a readable table + the 2x2 tables
    mcnemar_chart.png      accuracy chart annotated with Holm-adjusted significance
    discordant_tasks.csv   every task where the two conditions disagree (for error analysis)
"""
import argparse, json, pathlib, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.stats import binom
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.multitest import multipletests
from task import load_tasks

RESULTS = pathlib.Path(__file__).resolve().parent / "results"
ap = argparse.ArgumentParser()
ap.add_argument("--raw", default=str(RESULTS / "raw.jsonl"))
ap.add_argument("--outdir", default=str(RESULTS))
ap.add_argument("--rater", default="rater1", help="whose human grades to use")
ap.add_argument("--threshold", type=float, default=0.5, help="share of correct reps needed (default 0.5)")
ap.add_argument("--alpha", type=float, default=0.05)
a = ap.parse_args()
for s in (sys.stdout, sys.stderr):
    if hasattr(s, "reconfigure"): s.reconfigure(encoding="utf-8", errors="replace")
out = pathlib.Path(a.outdir); out.mkdir(parents=True, exist_ok=True)

# ---------- load + grade ----------
tasks = {t["id"]: t for t in load_tasks()}
df = pd.DataFrame(json.loads(l) for l in open(a.raw, encoding="utf-8"))
hp = out / f"human_{a.rater}.jsonl"
human = {}
if hp.exists():
    for l in hp.open(encoding="utf-8"):
        r = json.loads(l); human[r["key"]] = r["correct"]
else:
    print(f"NOTE: {hp} not found; human-graded tasks will be excluded.")
df["key"] = df.task_id + "|" + df.condition + "|" + df.rep.astype(str)
df["correct"] = df.auto_correct.where(df.auto_correct.notna(), df.key.map(human))
if df.correct.isna().any():
    print(f"WARNING: {int(df.correct.isna().sum())} ungraded runs excluded.")
df = df[df.correct.notna()].copy(); df["correct"] = df.correct.astype(float)

piv = df.pivot_table(index=["category", "task_id"], columns="condition", values="correct").dropna()
piv["react_ok"] = piv.react >= a.threshold
piv["no_react_ok"] = piv.no_react >= a.threshold

# ---------- McNemar per group ----------
def mcn(s):
    A, B = s.react_ok.values, s.no_react_ok.values
    both, b, c, neither = int((A & B).sum()), int((A & ~B).sum()), int((~A & B).sum()), int((~A & ~B).sum())
    n = b + c
    p = float(mcnemar([[both, b], [c, neither]], exact=True).pvalue) if n else 1.0
    m = min(b, c)
    p_mid = max(0.0, p - binom.pmf(m, n, 0.5)) if n else 1.0
    return dict(n_tasks=len(s), both_correct=both, react_only=b, no_react_only=c, both_wrong=neither,
                acc_react=A.mean(), acc_no_react=B.mean(), diff=A.mean() - B.mean(),
                discordant=n, odds_ratio=(b + .5) / (c + .5), p_exact=p, p_mid=p_mid)

rows = {"ALL": mcn(piv)}
for cat, s in piv.groupby(level="category"): rows[cat] = mcn(s)
res = pd.DataFrame(rows).T
for col in ["n_tasks", "both_correct", "react_only", "no_react_only", "both_wrong", "discordant"]:
    res[col] = res[col].astype(int)
m = res.index != "ALL"                       # correction over the category tests; ALL is a separate pooled test
res["p_holm"] = np.nan; res["p_bonferroni"] = np.nan
res.loc[m, "p_holm"] = multipletests(res.loc[m, "p_exact"].astype(float), method="holm")[1]
res.loc[m, "p_bonferroni"] = multipletests(res.loc[m, "p_exact"].astype(float), method="bonferroni")[1]
res["p_adj"] = res.p_holm.fillna(res.p_exact)  # ALL uses its raw p
res["significant"] = res.p_adj < a.alpha
res["direction"] = np.where(res.react_only > res.no_react_only, "ReAct better",
                     np.where(res.react_only < res.no_react_only, "no-ReAct better", "tie"))
res.to_csv(out / "mcnemar.csv", encoding="utf-8")

# ---------- discordant tasks ----------
d = piv[piv.react_ok != piv.no_react_ok].reset_index()
d["winner"] = np.where(d.react_ok, "react", "no_react")
d["question"] = d.task_id.map(lambda i: tasks[i]["question"])
d[["category", "task_id", "winner", "react", "no_react", "question"]].rename(
    columns={"react": "react_acc", "no_react": "no_react_acc"}).to_csv(
    out / "discordant_tasks.csv", index=False, encoding="utf-8")

# ---------- console + markdown ----------
stars = lambda p: "***" if p < .001 else "**" if p < .01 else "*" if p < a.alpha else "ns"
fmt = lambda v: f"{v:.4f}" if isinstance(v, (float, np.floating)) else str(v)
cols = ["n_tasks", "acc_react", "acc_no_react", "diff", "react_only", "no_react_only",
        "odds_ratio", "p_exact", "p_mid", "p_holm", "direction"]
head = "| group | " + " | ".join(cols) + " | sig |\n|" + "---|" * (len(cols) + 2)
lines = [head] + ["| " + " | ".join([i] + ["" if pd.isna(r[c]) else fmt(r[c]) for c in cols] + [stars(r.p_adj)]) + " |"
                  for i, r in res.iterrows()]
tables = []
for i, r in res.iterrows():
    tables.append(f"**{i}** (n={r.n_tasks})\n\n|  | no-ReAct correct | no-ReAct wrong |\n|---|---|---|\n"
                  f"| **ReAct correct** | {r.both_correct} | {r.react_only} |\n"
                  f"| **ReAct wrong** | {r.no_react_only} | {r.both_wrong} |\n")
md = ["# McNemar tests: ReAct vs no-ReAct", "",
      f"Rule: a task counts as correct in a condition if >= {a.threshold:.0%} of its reps were correct. "
      f"Exact (two-sided) McNemar; `p_mid` = mid-p variant; `p_holm` = Holm over the {int(m.sum())} categories "
      f"(ALL excluded, its `sig` uses the raw p). `odds_ratio` = (react_only+.5)/(no_react_only+.5). "
      f"sig: * p<{a.alpha}, ** p<.01, *** p<.001 (adjusted), ns = not significant.", "",
      *lines, "", "## Contingency tables", "", *tables]
(out / "mcnemar.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))

# ---------- chart ----------
fig, ax = plt.subplots(figsize=(9, 4.5)); x = np.arange(len(res)); w = .38
ax.bar(x - w/2, res.acc_react.astype(float), w, label="ReAct")
ax.bar(x + w/2, res.acc_no_react.astype(float), w, label="No ReAct")
for xi, (_, r) in zip(x, res.iterrows()):
    ax.text(xi, max(r.acc_react, r.acc_no_react) + .03, stars(r.p_adj), ha="center", fontsize=11)
ax.set_xticks(x); ax.set_xticklabels([f"{i}\n(+{r.react_only}/-{r.no_react_only})" for i, r in res.iterrows()],
                                     fontsize=8)
ax.set_ylim(0, 1.12); ax.set_ylabel("Accuracy (mean over tasks)")
ax.set_title("ReAct vs no-ReAct  (stars: McNemar, Holm-adjusted; +x/-y = ReAct-only / no-ReAct-only wins)", fontsize=9)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False)
plt.tight_layout(); plt.savefig(out / "mcnemar_chart.png", dpi=160, bbox_inches="tight")
print(f"\nSaved to {out}: mcnemar.csv, mcnemar.md, mcnemar_chart.png, discordant_tasks.csv")
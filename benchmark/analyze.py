"""python analyze.py --rater rater1 [--rater2 rater2]   ->  results/report.md, summary.csv, figures"""
import argparse, json, pathlib, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.stats import wilcoxon
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.multitest import multipletests
from task import load_tasks

RESULTS = pathlib.Path(__file__).resolve().parent / "results"

ap = argparse.ArgumentParser()
ap.add_argument("--raw", default=str(RESULTS / "raw.jsonl")); ap.add_argument("--rater", default="rater1")
ap.add_argument("--rater2", default=None); ap.add_argument("--outdir", default=str(RESULTS))
a = ap.parse_args(); out = pathlib.Path(a.outdir)

tasks = {t["id"]: t for t in load_tasks()}
df = pd.DataFrame(json.loads(l) for l in open(a.raw, encoding="utf-8"))
df["key"] = df.task_id + "|" + df.condition + "|" + df.rep.astype(str)

def load_h(r):
    p = out / f"human_{r}.jsonl"
    return {json.loads(l)["key"]: json.loads(l)["correct"] for l in p.open(encoding="utf-8")} if p.exists() else {}
h1 = load_h(a.rater)
df["human"] = df.key.map(h1)
df["correct"] = df.auto_correct.where(df.auto_correct.notna(), df.human)
ungraded = df.correct.isna().sum()
if ungraded: print(f"WARNING: {ungraded} runs not graded yet; excluded from stats")
df = df[df.correct.notna()].copy(); df["correct"] = df.correct.astype(float)

# ---------- paired accuracy (task = unit of analysis; reps averaged) ----------
piv = df.pivot_table(index=["category", "task_id"], columns="condition", values="correct").dropna()
piv["diff"] = piv.react - piv.no_react

def boot_ci(x, n=10000, seed=0):
    rng = np.random.default_rng(seed); x = np.asarray(x)
    m = rng.choice(x, (n, len(x))).mean(1); return np.percentile(m, [2.5, 97.5])

def compare(s):
    d = s["diff"].values; A, B = (s.react >= .5).values, (s.no_react >= .5).values
    b, c = int((A & ~B).sum()), int((~A & B).sum())          # discordant pairs
    tbl = [[int((A & B).sum()), b], [c, int((~A & ~B).sum())]]
    lo, hi = boot_ci(d)
    return dict(n_tasks=len(d), acc_react=s.react.mean(), acc_no_react=s.no_react.mean(),
                diff=d.mean(), ci_lo=lo, ci_hi=hi, react_only_wins=b, no_react_only_wins=c,
                p_mcnemar=mcnemar(tbl, exact=True).pvalue,
                p_wilcoxon=wilcoxon(d).pvalue if np.any(d != 0) else 1.0)

rows = {"ALL": compare(piv)}
for cat, s in piv.groupby(level="category"): rows[cat] = compare(s)
res = pd.DataFrame(rows).T
m = res.index != "ALL"
res.loc[m, "p_holm"] = multipletests(res.loc[m, "p_mcnemar"].astype(float), method="holm")[1]
res.to_csv(out / "summary.csv")

# ---------- run-level GEE (uses every run, clusters by task) ----------
gee_txt = ""
try:
    import statsmodels.formula.api as smf, statsmodels.api as sm
    d2 = df.assign(react=(df.condition == "react").astype(int))
    g = smf.gee("correct ~ react", groups="task_id", data=d2, family=sm.families.Binomial(),
                cov_struct=sm.cov_struct.Exchangeable()).fit()
    gee_txt = f"GEE logistic (clustered by task): OR = {np.exp(g.params['react']):.2f}, p = {g.pvalues['react']:.4f}"
except Exception as e:
    gee_txt = f"GEE failed: {e}"

# ---------- secondary metrics ----------
sec = []
for met in ("latency", "steps"):
    p = df.pivot_table(index="task_id", columns="condition", values=met).dropna()
    d = p.react - p.no_react
    sec.append((met, p.react.mean(), p.no_react.mean(), wilcoxon(d).pvalue if np.any(d != 0) else 1.0))
rr = df[df.condition == "react"].copy()
rr["n_calls"] = rr.tool_calls.apply(len)
rr["exp"] = rr.task_id.map(lambda i: set(tasks[i]["tools_expected"]))
rr["used"] = rr.tool_calls.apply(set)
nt = rr[rr.category == "no_tool"]
tool_txt = [f"No-tool tasks where ReAct called a tool anyway: {(nt.n_calls > 0).mean():.1%} (n={len(nt)})"]
need = rr[rr.exp.apply(len) > 0]
tool_txt.append(f"Tool-requiring tasks where all expected tools were used: "
                f"{(need.apply(lambda r: r.exp <= r.used, axis=1)).mean():.1%} (n={len(need)})")
tool_txt.append(f"ReAct error/timeout rate: {(rr.error.notna()).mean():.1%}; "
                f"no-ReAct: {(df[df.condition=='no_react'].error.notna()).mean():.1%}")

# ---------- inter-rater agreement ----------
kappa_txt = ""
if a.rater2:
    from sklearn.metrics import cohen_kappa_score
    h2 = load_h(a.rater2); ks = [k for k in h1 if k in h2]
    if ks:
        k = cohen_kappa_score([h1[x] for x in ks], [h2[x] for x in ks])
        kappa_txt = f"Cohen's kappa ({a.rater} vs {a.rater2}, n={len(ks)}): {k:.3f}; raw agreement {np.mean([h1[x]==h2[x] for x in ks]):.1%}"

# ---------- figure ----------
fig, ax = plt.subplots(figsize=(8, 4)); cats = list(res.index); x = np.arange(len(cats)); w = .38
ax.bar(x - w/2, res.acc_react.astype(float), w, label="ReAct")
ax.bar(x + w/2, res.acc_no_react.astype(float), w, label="No ReAct")
ax.set_xticks(x); ax.set_xticklabels(cats, rotation=30, ha="right"); ax.set_ylim(0, 1.05)
ax.set_ylabel("Accuracy (mean over tasks)"); ax.legend(); plt.tight_layout()
plt.savefig(out / "accuracy_by_category.png", dpi=160)

# ---------- report ----------
def md(df_, fmt):
    h = "| " + " | ".join(["group"] + list(df_.columns)) + " |\n|" + "---|" * (len(df_.columns) + 1) + "\n"
    return h + "\n".join("| " + " | ".join([str(i)] + [fmt(v) for v in r]) + " |" for i, r in df_.iterrows())
f = lambda v: "" if pd.isna(v) else (f"{v:.3f}" if isinstance(v, (float, np.floating)) else str(v))
tbl = res[["n_tasks", "acc_react", "acc_no_react", "diff", "ci_lo", "ci_hi", "react_only_wins",
           "no_react_only_wins", "p_mcnemar", "p_holm"]]
rep = ["# Benchmark report", "",
       (f"Run meta: `{(out / 'run_meta.json').read_text(encoding='utf-8').strip()}`".replace("\n", " ") if (out / "run_meta.json").exists() else ""),
       "", "## Accuracy: ReAct vs no-ReAct (paired by task)", "", md(tbl, f), "",
       "`diff` = ReAct − no-ReAct accuracy, 95% bootstrap CI over tasks. p_mcnemar: exact McNemar on majority-vote "
       "outcomes. p_holm: Holm-corrected across categories (ALL excluded).", "",
       "![accuracy](accuracy_by_category.png)", "", "## Run-level model", "", gee_txt, "",
       "## Secondary metrics (paired Wilcoxon over tasks)", "",
       "| metric | react | no_react | p |\n|---|---|---|---|\n" +
       "\n".join(f"| {m_} | {r:.3f} | {n:.3f} | {p:.4f} |" for m_, r, n, p in sec), "",
       "## Tool behaviour (ReAct only)", ""] + [f"- {t}" for t in tool_txt] + \
      (["", "## Grading reliability", "", kappa_txt] if kappa_txt else [])
(out / "report.md").write_text("\n".join(rep), encoding="utf-8")
print("\n".join(rep))
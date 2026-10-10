"""Blinded human grading.  streamlit run human_eval.py -- --rater alice
Condition and tool calls are hidden. Resume-safe: grades append to results/human_<rater>.jsonl.
A second rater should grade ~20% (use --sample 0.2) for Cohen's kappa."""
import argparse, json, random, pathlib, streamlit as st
from task import load_tasks

RESULTS = pathlib.Path(__file__).resolve().parent / "results"

p = argparse.ArgumentParser(); p.add_argument("--rater", default="rater1")
p.add_argument("--sample", type=float, default=1.0); p.add_argument("--raw", default=str(RESULTS / "raw.jsonl"))
a, _ = p.parse_known_args()

key = lambda r: f"{r['task_id']}|{r['condition']}|{r['rep']}"
tasks = {t["id"]: t for t in load_tasks()}
rows = [json.loads(l) for l in open(a.raw, encoding="utf-8")]
need = [r for r in rows if tasks[r["task_id"]]["grader"] == "human" and r["error"] is None]
need.sort(key=key); random.Random(42).shuffle(need)          # same blinded order for every rater
if a.sample < 1: need = need[: int(len(need) * a.sample)]

path = RESULTS / f"human_{a.rater}.jsonl"
done = {json.loads(l)["key"] for l in path.open(encoding="utf-8")} if path.exists() else set()
todo = [r for r in need if key(r) not in done]
st.caption(f"Rater: {a.rater}")
st.progress(1 - len(todo) / max(1, len(need)), text=f"{len(need)-len(todo)}/{len(need)} graded")
if not todo:
    st.success("All graded."); st.stop()

r = todo[0]; t = tasks[r["task_id"]]
st.subheader(t["question"])
st.info(f"Rubric: {t.get('rubric','')}")
st.markdown(r["answer"] or "_(empty answer)_")

def save(v):
    with path.open("a", encoding="utf-8") as f: f.write(json.dumps({"key": key(r), "correct": v}, ensure_ascii=False) + "\n")
    st.rerun()
c1, c2 = st.columns(2)
if c1.button("✅ Correct", use_container_width=True): save(True)
if c2.button("❌ Incorrect", use_container_width=True): save(False)
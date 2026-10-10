"""Re-apply the automatic graders to an existing raw.jsonl (no model calls).
Use after fixing a grader or an `expected` value in tasks/*.json.

    python benchmark/regrade.py                      # regrade benchmark/results/raw.jsonl in place
    python benchmark/regrade.py --raw path/to/raw.jsonl --show-changes

Time-relative tasks are graded against each row's own `run_date`, so results stay correct.
A backup is written to <file>.bak first. Rows with a run error stay incorrect.
"""
import argparse, datetime as dt, json, pathlib, shutil
from benchmark.task import load_tasks
from benchmark.graders import grade

RESULTS = pathlib.Path(__file__).resolve().parent / "results"
ap = argparse.ArgumentParser()
ap.add_argument("--raw", default=str(RESULTS / "raw.jsonl"))
ap.add_argument("--show-changes", action="store_true")
a = ap.parse_args()

path = pathlib.Path(a.raw)
tasks = {t["id"]: t for t in load_tasks()}
rows = [json.loads(l) for l in path.open(encoding="utf-8")]
shutil.copy(path, str(path) + ".bak")

changed = 0
for r in rows:
    t = tasks.get(r["task_id"])
    if t is None:
        continue
    day = dt.date.fromisoformat(r["run_date"]) if r.get("run_date") else None
    new = False if r.get("error") else grade(t, r["answer"], day)
    if new != r["auto_correct"]:
        changed += 1
        if a.show_changes:
            print(f"{r['task_id']} [{r['condition']}] {r['auto_correct']} -> {new} | {r['answer'][:100]!r}")
        r["auto_correct"] = new

with path.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"{len(rows)} rows, {changed} grades changed (backup: {path}.bak)")
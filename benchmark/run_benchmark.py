import argparse, json, random, time, pathlib, subprocess, sys, datetime as dt
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FTimeout
from benchmark.task import load_tasks
from benchmark.graders import grade

RESULTS = pathlib.Path(__file__).resolve().parent / "results"


def mock_agent(task, use_react):
    """Pipeline test only: pretends to be an agent (react is 'better')."""
    time.sleep(0.01)
    ok = random.random() < (0.85 if use_react else 0.6)
    g, e = task["grader"], task["expected"]
    ans = "I don't know."
    if ok and g in ("numeric",): ans = f"The answer is {e}"
    elif ok and g == "contains": ans = " ".join(e)
    elif ok and g == "human": ans = "Plausible answer (mock)."
    calls = list(task["tools_expected"]) if use_react else []
    return {"answer": ans, "tool_calls": calls, "steps": len(calls) + 1}


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return None


def main(a):
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy codepage
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    random.seed(a.seed)
    effective = {}
    if a.mock:
        run = None
    else:
        import adapter
        effective = adapter.configure(model=a.model, temperature=a.temperature, max_steps=a.max_steps)
        run = adapter.run_agent
        print("Effective settings:", effective)
    tasks = load_tasks(categories=a.categories)
    out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for l in out.open(encoding="utf-8"):
            r = json.loads(l); done.add((r["task_id"], r["condition"], r["rep"]))
    jobs = [(t, c, r) for t in tasks for c in ("react", "no_react") for r in range(a.k)
            if (t["id"], c, r) not in done]
    random.shuffle(jobs)  # avoid order / time-of-day bias between conditions
    meta = {"started": dt.datetime.now().isoformat(), "git": git_commit(), "k": a.k, "seed": a.seed,
            "n_tasks": len(tasks), "settings": effective, "mock": a.mock}
    (out.parent / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"{len(jobs)} runs to do ({len(done)} already done)")
    with out.open("a", encoding="utf-8") as f:
        for n, (t, cond, rep) in enumerate(jobs, 1):
            t0, err = time.time(), None
            ex = ThreadPoolExecutor(max_workers=1)  # fresh per job: a hung run can't block the next
            try:
                fut = ex.submit(mock_agent, t, cond == "react") if a.mock else \
                      ex.submit(run, t["question"], cond == "react")
                res = fut.result(timeout=a.timeout)
            except FTimeout:
                res, err = None, "timeout"
            except Exception as e:
                res, err = None, f"{type(e).__name__}: {e}"
            finally:
                ex.shutdown(wait=False)
            if res is None:  # errors/timeouts count as INCORRECT, never dropped
                res = {"answer": "", "tool_calls": [], "steps": 0}
            elif res.get("error"):  # agent-level failure (format error, max steps, ...)
                err = res["error"]
            row = {"task_id": t["id"], "category": t["category"], "condition": cond, "rep": rep,
                   "answer": res["answer"], "tool_calls": res["tool_calls"], "steps": res["steps"],
                   "latency": round(time.time() - t0, 3), "error": err,
                   "run_date": dt.date.today().isoformat(),
                   "auto_correct": grade(t, res["answer"]) if err is None else False}
            f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush()
            if n % 25 == 0: print(f"{n}/{len(jobs)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(RESULTS / "raw.jsonl"))
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--categories", nargs="*", default=None)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--model", default=None, help="override config.yaml llm.model")
    p.add_argument("--temperature", type=float, default=None, help="override config.yaml llm.temperature")
    p.add_argument("--max-steps", type=int, default=None, help="override config.yaml agent.max_steps")
    p.add_argument("--mock", action="store_true", help="test the pipeline without your agent")
    main(p.parse_args())
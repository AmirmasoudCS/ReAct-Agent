import json, pathlib

TASK_DIR = pathlib.Path(__file__).parent / "tasks"
REQUIRED = {"id", "category", "question", "grader", "expected", "tools_expected"}
GRADERS = {"numeric", "contains", "regex", "dynamic", "human"}


def load_tasks(task_dir=TASK_DIR, categories=None):
    tasks, seen = [], set()
    for f in sorted(pathlib.Path(task_dir).glob("*.json")):
        for t in json.loads(f.read_text(encoding="utf-8")):
            missing = REQUIRED - t.keys()
            assert not missing, f"{f.name}:{t.get('id')} missing {missing}"
            assert t["grader"] in GRADERS, f"{t['id']}: bad grader"
            assert t["id"] not in seen, f"duplicate id {t['id']}"
            seen.add(t["id"])
            if categories is None or t["category"] in categories:
                tasks.append(t)
    return tasks


if __name__ == "__main__":
    from collections import Counter
    ts = load_tasks()
    print(len(ts), "tasks")
    for c, n in Counter(t["category"] for t in ts).items():
        auto = sum(1 for t in ts if t["category"] == c and t["grader"] != "human")
        print(f"  {c:12s} {n:3d}  auto-graded: {auto}")
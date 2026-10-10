# ReAct vs. No-ReAct Benchmark

A small, reproducible benchmark that compares the same LLM with and without the ReAct tool loop,
on tasks that need tools (calculator, datetime, weather, web search, Wikipedia, combinations of
these) and tasks that should not need any tool. It covers task definitions, automatic grading,
blinded human grading, paired statistical tests and an auto-generated report.

## 1. What is compared

| Condition | What runs |
|---|---|
| `react` | A **fresh** `ReActAgent` per run (empty history), the full tool registry, the ReAct system prompt, `max_steps` from `adapter.py`. |
| `no_react` | The **same** `LLMClient`, **no tools** and no ReAct prompt: a single plain completion with a short generic system prompt. |

Everything else (model, temperature, tasks) is identical, so the data is **paired by task**.
Each task is run `k` times per condition because LLM output is stochastic.

## 2. Layout

```
benchmark/
├── tasks/                 one JSON array per category (180 tasks total)
│   ├── calculator.json    30  (auto-graded)
│   ├── datetime.json      30  (auto-graded, time-relative answers computed at run time)
│   ├── wikipedia.json     30  (auto-graded)
│   ├── no_tool.json       30  (auto-graded; tools should NOT be used)
│   ├── multi_tool.json    20  (10 auto, 10 human)
│   ├── web_search.json    20  (8 auto, 12 human)
│   └── weather.json       20  (human)
├── task.py                loads + validates all task files (python benchmark/task.py for counts)
├── graders.py             automatic graders
├── adapter.py             the ONLY file that touches the agent code
├── run_benchmark.py       runs tasks under both conditions, writes results/raw.jsonl
├── human_eval.py          blinded Streamlit grading UI
├── analyze.py             statistics + report
└── results/               created on first run
    ├── raw.jsonl          one row per run
    ├── run_meta.json      model tag, temperature, seed, k, git commit
    ├── human_<rater>.jsonl
    ├── summary.csv
    ├── accuracy_by_category.png
    └── report.md
```

## 3. Setup

```bash
pip install pandas scipy statsmodels matplotlib scikit-learn streamlit
```

Run every command **from the project root** (so `config.yaml` and the package imports resolve):

```bash
python benchmark/task.py        # sanity check: lists categories, counts, auto vs human
```

### Settings

`adapter.py` is already wired to this project (`LLMClient`, the five tools, `ReActAgent`). Settings are
read from **`config.yaml`** (model, temperature, `top_p`, stop sequences, `max_output_tokens`,
`agent.max_steps`, tool timeout) and **not** from `settings.json`, which stores UI tweaks and would
make runs depend on whatever was last clicked in the frontend. Override per run with
`--model`, `--temperature`, `--max-steps`. The effective settings (including the reasoning effort)
are printed at start and saved in `results/run_meta.json`.

Notes on how the conditions are built:
- `react` uses `ReActAgent` with **no `ContextManager`** (single-turn runs do not need compaction).
- `no_react` calls `generate_response(..., stop=[])`. The client's default stop sequences
  (`PAUSE`, `Observation:`) are disabled, otherwise they could truncate plain answers.
- Both conditions share the same `top_p`, `max_output_tokens` and reasoning effort
  (`OLLAMA_REASONING_EFFORT`, default `none`).
- Each model call has a 120 s HTTP timeout, and each run a `--timeout` (default 180 s) wall-clock limit.
- Tool names must match the registry: `calculator`, `datetime`, `weather`, `web_search`, `wikipedia_search`.

## 4. Running

```bash
# Pipeline test without your agent (fake answers; numbers are meaningless)
python benchmark/run_benchmark.py --mock --k 1 --out /tmp/mock/raw.jsonl

# Small real smoke test (check results/raw.jsonl afterwards)
python benchmark/run_benchmark.py --categories calculator no_tool --k 1 --temperature 0

# Full runs
python benchmark/run_benchmark.py --k 1 --temperature 0                                          # deterministic pass
python benchmark/run_benchmark.py --k 5 --out benchmark/results/raw_t02.jsonl                    # stochastic pass (config temperature)
```

Options: `--k` repetitions per task and condition, `--seed` for job order, `--categories` to
restrict, `--model`, `--temperature`, `--max-steps` (override `config.yaml`), `--timeout` seconds per
run (default 180), `--out` output file, `--mock`.

Use a separate `--out` file for each configuration. `analyze.py --raw <file>` analyses one file at a time.

Properties of the runner:
- **Resume-safe**: re-running skips `(task, condition, rep)` triples already in the output file.
- **Randomized order** across tasks and conditions, to avoid time-of-day or rate-limit bias.
- **Failures count as incorrect, never dropped**: exceptions, timeouts, and agent-level errors
  (max steps reached, repeated invalid format) are stored in the `error` field with an empty or
  partial answer and `auto_correct=false`. Dropping them would favour whichever condition crashes more.
- **Dynamic answers graded at run time**: "what weekday is 100 days from today?" is graded using the
  date of the run (stored as `run_date`), so the result cannot drift.

Each row in `raw.jsonl`: `task_id, category, condition, rep, answer, tool_calls, steps, latency,
error, run_date, auto_correct` (`null` = needs human grading).

## 5. Task format

```json
{"id": "calc_001", "category": "calculator", "question": "...",
 "grader": "numeric", "expected": 432977.0, "tol": 0.01,
 "tools_expected": ["calculator"]}
```

| Field | Meaning |
|---|---|
| `grader` | `numeric`, `contains`, `regex`, `dynamic`, or `human` |
| `expected` | Depends on grader (number, list of substrings, regex, dynamic spec, or `null`) |
| `tol` | Absolute tolerance for `numeric` (default 1e-6) |
| `tools_expected` | Tools that should be called (all of them). Empty list means no tool needed |
| `rubric` | Shown to human raters |
| `notes` | Free text (e.g. "re-verify before each run") |

Graders (`graders.py`):
- `numeric`: **any** number in the answer within `tol` of `expected` (commas handled).
- `contains`: **all** substrings present, case-insensitive.
- `regex`: `re.search`.
- `dynamic`: `expected` is a spec such as `{"fn": "days_until", "month": 12, "day": 25}`. Supported
  `fn`: `weekday_plus, current_weekday, current_year, current_month, date_plus, days_until,
  day_of_year, days_since, year_diff, full_years_since`.
- `human`: graded in the UI.

**Adding tasks:** append objects to the matching JSON file with a unique `id`; `task.py` validates
required fields and duplicate ids. Keep a held-out split and **do not tune prompts on benchmark tasks**.

**Known grader limitation:** `numeric` and `contains` are lenient on purpose (the answer may
contain other numbers). Spot-check a sample of auto-graded answers by hand; the human UI can be
pointed at them if you want a validity check.

## 6. Human grading

```bash
streamlit run benchmark/human_eval.py -- --rater alice
streamlit run benchmark/human_eval.py -- --rater bob --sample 0.2   # second rater on 20%
```

- Shows question, rubric and answer only. **Condition and tool calls are hidden** (blinded),
  and the order is shuffled with a fixed seed so every rater sees the same sequence.
- Grades append to `results/human_<rater>.jsonl`; closing the browser loses nothing.
- Only tasks with `grader: "human"` (and no run error) are shown.
- Live-data tasks (weather, search) should be graded **soon after the run**, because "correct
  right now" changes. Rubrics ask the rater to check against a quick manual lookup.
- A second rater on ~20% gives Cohen's kappa in the report. Kappa above 0.6 is usually
  considered acceptable agreement.

## 7. Analysis and report

```bash
python benchmark/analyze.py --rater alice --rater2 bob
```

Outputs to `benchmark/results/`: `report.md`, `summary.csv`, `accuracy_by_category.png`.
Runs not yet graded are excluded (a warning prints the count).

Method:
- **Unit of analysis = task.** Per-task accuracy (mean over reps) per condition; paired by task.
- **Effect size**: mean difference ReAct minus no-ReAct, with a 95% bootstrap CI (resampling tasks).
- **Primary test**: exact **McNemar** on majority-vote outcomes (≥50% of reps correct). Only
  *discordant* tasks matter, and the report shows their counts (`react_only_wins`, `no_react_only_wins`).
- **Multiple comparisons**: **Holm** correction across the category tests (`p_holm`). The `ALL` row is a
  separate pooled test and is not included in the correction.
- **Run-level model**: logistic **GEE** clustered by task (exchangeable), giving an odds ratio that uses
  every run rather than majority votes.
- **Secondary metrics**: latency and steps with paired **Wilcoxon**; unnecessary tool calls on
  `no_tool` tasks; share of tool tasks where all expected tools were used; error/timeout rates.
- **Reliability**: Cohen's kappa between raters when `--rater2` is given.

Reading the results:
- Report the **CI**, not only the p-value. With 20 to 30 tasks per category, a non-significant
  result is **not** evidence of "no difference".
- A pooled `ALL` result can hide a category where ReAct hurts (typically `no_tool`).
- Latency and steps are expected to be higher for ReAct; this is a cost, not an accuracy effect.
- Multiple k values or temperatures should be reported separately, not pooled.

## 8. Reproducibility checklist

- Model, temperature, max steps, top_p, stop sequences, reasoning effort, `k`, seed and git commit are all in `run_meta.json`.
- Run both conditions in the same session; the runner interleaves them randomly.
- Live tools (weather/search) change over time. Grade promptly, or log tool outputs and replay them.
- Keep `raw.jsonl` and the `human_*.jsonl` files together with the report.
- Use a clean checkout (the git commit is stored in `run_meta.json`).

## 9. What the comparison does and does not show

`react` is the **whole agent** (ReAct loop + tools + a long, rule-heavy system prompt) and `no_react` is
the **bare model** with a short prompt. The measured difference therefore bundles three things: tool
access, the ReAct reasoning format, and the prompt's routing rules (for example "never guess the
current date"). It answers "does the agent beat the bare model?", not "does the Thought/Action format
itself help?". To isolate the format you would add a third condition, such as tools without the ReAct
format (native function calling), or ReAct with all tools but a minimal prompt. Also note that
`no_react` is told to say so when it cannot know something, so on live-data tasks it fails honestly
instead of guessing. State this choice in the write-up.

## 10. Failure analysis (recommended for the write-up)

`raw.jsonl` keeps `error`, `tool_calls` and `steps`, so you can categorise failures per condition:
wrong tool chosen, tool never called when needed, unnecessary tool call, repeated invalid format,
max steps reached, wrong final computation, timeout. A short table of these usually explains the
accuracy differences better than the p-values.

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| Connection errors / all rows fail | Is Ollama running and the model pulled? Check `OLLAMA_BASE_URL`. |
| Many `react` rows have `error: ...maximum number of steps` | Raise `--max-steps`, or inspect the traces of those rows. |
| Many empty answers | Thinking models can leave `content` empty; check `OLLAMA_REASONING_EFFORT` and `max_output_tokens`. |
| `no_react` answers contain strange prefixes | The adapter strips `<channel|>` markers; extend `_clean()` for other markers. |
| `datetime` tasks all wrong for both conditions | Check the machine clock/timezone and that the datetime tool returns today's date. |
| `ModuleNotFoundError: task` | Run scripts from the project root as shown (`python benchmark/...`). |
| Human UI shows nothing to grade | No human-graded rows in `raw.jsonl` yet, or all are graded. |
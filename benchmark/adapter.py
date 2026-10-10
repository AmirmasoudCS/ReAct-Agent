"""The ONLY file that touches your agent code.

run_agent(question, use_react) -> {"answer": str, "tool_calls": [names], "steps": int, "error": str|None}

  react    = a FRESH ReActAgent per run (no shared history), full tool registry, ReAct prompt.
  no_react = same LLMClient, NO tools, NO ReAct prompt: a single plain completion.

Run the benchmark from the PROJECT ROOT so config.yaml etc. resolve:
    python benchmark/run_benchmark.py ...
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MAX_STEPS = 8  # ReAct step budget (same for every task; report it in the write-up)

NO_REACT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question directly and concisely. "
    "If you cannot know something (for example live data), say so."
)

_llm = None
_tools = None


# ----------------------------------------------------------------------------------
# TODO: make these two functions build things EXACTLY like main.py / api.py do.
# They are the only guesses in this file (I haven't seen llm/client.py,
# tools/registry.py or main.py). Temperature should be set here too (0 for the main run).
# ----------------------------------------------------------------------------------
def build_llm():
    from llm.client import LLMClient
    from utils.config import load_config  # TODO: adjust to your real config loader

    cfg = load_config()
    return LLMClient(**cfg["llm"])  # TODO: adjust constructor arguments


def build_tools():
    from tools.registry import ToolRegistry  # TODO: adjust how tools are registered

    registry = ToolRegistry()
    # e.g. registry.register(Calculator()); registry.register(Weather()); ...
    return registry


def _get():
    global _llm, _tools
    if _llm is None:
        _llm, _tools = build_llm(), build_tools()
    return _llm, _tools


def _clean(text: str) -> str:
    """Drop model 'thinking channel' prefixes if present (same marker agent.py handles)."""
    import re
    parts = re.split(r"<\s*channel\s*\|\s*>", text, flags=re.IGNORECASE)
    return parts[-1].strip()


def _run_react(question: str) -> dict:
    from agent import ReActAgent

    llm, tools = _get()
    agent = ReActAgent(llm, tools, max_steps=MAX_STEPS)  # fresh history every run
    calls, answer, error = [], "", None
    for ev in agent.run_stream(question, stream_tokens=False):
        if ev["type"] == "action":
            calls.append(ev["tool_name"])
        elif ev["type"] == "final":
            answer = ev["content"]
        elif ev["type"] == "error":
            error = ev["message"]  # e.g. max steps / repeated invalid format
    return {"answer": answer, "tool_calls": calls, "steps": len(calls) + 1, "error": error}


def _run_plain(question: str) -> dict:
    from utils.message import Message

    llm, _ = _get()
    text = _clean(llm.generate_response(NO_REACT_SYSTEM_PROMPT, [Message("user", question)]))
    return {"answer": text, "tool_calls": [], "steps": 1,
            "error": None if text else "empty response"}


def run_agent(question: str, use_react: bool) -> dict:
    return _run_react(question) if use_react else _run_plain(question)
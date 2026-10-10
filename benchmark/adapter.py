"""The ONLY file that touches your agent code.

run_agent(question, use_react) -> {"answer", "tool_calls", "steps", "error"}

  react    = a FRESH ReActAgent per run (no shared history), the full tool registry, the ReAct
             system prompt, no ContextManager (single-turn runs never need compaction).
  no_react = the SAME LLMClient settings, NO tools, NO ReAct prompt: one plain completion.

Settings come from config.yaml (NOT settings.json, which holds UI tweaks), optionally
overridden via configure() / the runner's --model, --temperature, --max-steps flags.
Run from the PROJECT ROOT:  python benchmark/run_benchmark.py ...
"""
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NO_REACT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question directly and concisely. "
    "If you cannot know something (for example live data), say so."
)

_state: dict = {}


def configure(model=None, temperature=None, max_steps=None, request_timeout=120.0) -> dict:
    """Build the LLM client and tool registry once. Returns the effective settings (logged)."""
    from openai import OpenAI
    from llm.client import LLMClient
    from tools.calculator import CalculatorTool
    from tools.datetime import DateTimeTool
    from tools.registry import ToolRegistry
    from tools.weather import WeatherTool
    from tools.web_search import WebSearchTool
    from tools.wikipedia_search import WikipediaSearchTool
    from utils.config import load_config

    config = load_config()
    llm_cfg, ctx = config["llm"], config["context"]
    s = {
        "model": model or llm_cfg["model"],
        "temperature": llm_cfg["temperature"] if temperature is None else temperature,
        "max_steps": max_steps or config["agent"]["max_steps"],
        "top_p": llm_cfg["top_p"],
        "stop": llm_cfg["stop"],
        "max_output_tokens": ctx["max_output_tokens"],
        "tool_timeout": config["tools"]["timeout"],
        "request_timeout": request_timeout,
    }
    # An HTTP timeout bounds a hung model call, so a stuck run cannot block the benchmark.
    client = OpenAI(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        timeout=request_timeout,
        max_retries=1,
    )
    llm = LLMClient(model=s["model"], client=client, temperature=s["temperature"],
                    top_p=s["top_p"], stop=s["stop"], max_output_tokens=s["max_output_tokens"])
    s["reasoning_effort"] = llm.reasoning_effort

    t = s["tool_timeout"]
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    tools.register(DateTimeTool())
    tools.register(WikipediaSearchTool(timeout=t))
    tools.register(WebSearchTool(timeout=t))
    tools.register(WeatherTool(timeout=t))

    _state.update(llm=llm, tools=tools, settings=s)
    return s


def _get():
    if "llm" not in _state:
        configure()
    return _state["llm"], _state["tools"], _state["settings"]


def _clean(text: str) -> str:
    """Drop model 'thinking channel' prefixes if present (same marker agent.py handles)."""
    return re.split(r"<\s*channel\s*\|\s*>", text, flags=re.IGNORECASE)[-1].strip()


def _run_react(question: str) -> dict:
    from agent import ReActAgent

    llm, tools, s = _get()
    agent = ReActAgent(llm=llm, tools=tools, max_steps=s["max_steps"])  # fresh history
    calls, answer, error = [], "", None
    for ev in agent.run_stream(question, stream_tokens=False):
        if ev["type"] == "action":
            calls.append(ev["tool_name"])
        elif ev["type"] == "final":
            answer = ev["content"]
        elif ev["type"] == "error":
            error = ev["message"]  # max steps / repeated invalid or empty format
    return {"answer": answer, "tool_calls": calls, "steps": len(calls) + 1, "error": error}


def _run_plain(question: str) -> dict:
    from utils.message import Message

    llm, _, _ = _get()
    # stop=[] is essential: the client's default stop sequences ("PAUSE", "Observation:")
    # would otherwise truncate plain answers that happen to contain those strings.
    text = llm.generate_response(NO_REACT_SYSTEM_PROMPT, [Message("user", question)], stop=[])
    text = _clean(text)
    return {"answer": text, "tool_calls": [], "steps": 1,
            "error": None if text else "empty response"}


def run_agent(question: str, use_react: bool) -> dict:
    return _run_react(question) if use_react else _run_plain(question)
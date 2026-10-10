"""The ONLY file that touches your agent. Fill in run_agent().

Must return: {"answer": str, "tool_calls": [tool names in call order], "steps": int}
use_react=False must run the same model/temperature/system prompt style but with NO tools
available (not even described in the prompt) and no Thought/Action loop.
"""

def run_agent(question: str, use_react: bool) -> dict:
    raise NotImplementedError("Wire this to agent.py (share it and I'll write it).")
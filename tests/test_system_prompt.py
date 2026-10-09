
from prompts.system_prompt import build_system_prompt


def test_system_prompt_includes_available_tools():
    tools = "calculator: Performs arithmetic operations."

    prompt = build_system_prompt(tools)

    assert tools in prompt
    assert "Thought:" in prompt
    assert "Action:" in prompt
    assert "PAUSE" in prompt
    assert "Final Answer:" in prompt


def test_system_prompt_replaces_tools_placeholder():
    prompt = build_system_prompt("calculator: Performs arithmetic operations.")

    assert "{tools}" not in prompt
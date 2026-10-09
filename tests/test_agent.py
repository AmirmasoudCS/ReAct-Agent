import pytest

from agent import ReActAgent
from tools.calculator import CalculatorTool
from tools.registry import ToolRegistry


class FakeLLM:
    """Returns predefined responses instead of calling a real model."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = []

    def generate_response(self, system_prompt, messages):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "messages": list(messages),
            }
        )

        if not self.responses:
            raise AssertionError("No fake LLM responses left.")

        return self.responses.pop(0)


@pytest.fixture
def registry():
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    return tools


def test_returns_final_answer(registry):
    llm = FakeLLM(["Final Answer: Hello!"])
    agent = ReActAgent(llm, registry)

    assert agent.run("Say hello.") == "Hello!"
    assert len(llm.calls) == 1


def test_executes_tool_and_returns_final_answer(registry):
    llm = FakeLLM(
        [
            (
                'Thought: I need to calculate.\n'
                'Action: calculator: {"expression": "125 * 48"}\n'
                "PAUSE"
            ),
            "Final Answer: The result is 6000.",
        ]
    )
    agent = ReActAgent(llm, registry)

    result = agent.run("What is 125 times 48?")

    assert result == "The result is 6000."
    assert len(llm.calls) == 2

    second_call_messages = llm.calls[1]["messages"]
    assert second_call_messages[-1].content == "Observation: 6000"


def test_reports_unknown_tool_to_model(registry):
    llm = FakeLLM(
        [
            "Action: nonexistent: {}",
            "Final Answer: I could not use that tool.",
        ]
    )
    agent = ReActAgent(llm, registry)

    result = agent.run("Do something.")

    assert result == "I could not use that tool."
    assert (
        "does not exist"
        in llm.calls[1]["messages"][-1].content
    )


def test_retries_after_unparseable_response(registry):
    llm = FakeLLM(
        [
            "Thought: I need a tool, but the action is malformed.\n"
            "Action: wikipedia_search\nPAUSE",
            "Final Answer: Done.",

        ]
    )
    agent = ReActAgent(llm, registry)

    assert agent.run("Do something.") == "Done."
    assert len(llm.calls) == 2


def test_stops_at_max_steps(registry):
    llm = FakeLLM(
        [
            "Action: calculator: {invalid json}",
            "Action: calculator: {invalid json}",
        ]
    )
    agent = ReActAgent(llm, registry, max_steps=2)

    result = agent.run("Calculate something.")

    assert "maximum number of steps" in result
    assert len(llm.calls) == 2


def test_rejects_empty_user_input(registry):
    agent = ReActAgent(FakeLLM([]), registry)

    with pytest.raises(ValueError, match="cannot be empty"):
        agent.run("   ")


def test_rejects_invalid_max_steps(registry):
    with pytest.raises(ValueError, match="at least 1"):
        ReActAgent(FakeLLM([]), registry, max_steps=0)
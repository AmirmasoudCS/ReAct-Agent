
import pytest

from tools.base import BaseTool
from tools.calculator import CalculatorTool
from tools.registry import ToolRegistry


@pytest.fixture
def registry():
    result = ToolRegistry()
    result.register(CalculatorTool())
    return result


def test_register_and_get_tool(registry):
    tool = registry.get("calculator")

    assert isinstance(tool, CalculatorTool)


def test_get_unknown_tool_returns_none(registry):
    assert registry.get("unknown") is None


def test_get_descriptions_includes_calculator(registry):
    descriptions = registry.get_descriptions()

    assert "calculator" in descriptions
    assert "arithmetic" in descriptions.lower()


def test_execute_calculator(registry):
    result = registry.execute(
        "calculator",
        '{"expression": "125 * 48"}',
    )

    assert result == "6000"


def test_execute_unknown_tool_returns_error(registry):
    result = registry.execute("unknown", "{}")

    assert result.startswith("Error:")
    assert "unknown" in result


def test_duplicate_tool_registration_is_rejected(registry):
    with pytest.raises(ValueError, match="already registered"):
        registry.register(CalculatorTool())


def test_register_requires_a_tool():
    class InvalidTool(BaseTool):
        name = ""
        description = "Invalid tool"

        def execute(self, tool_input: str) -> str:
            return ""

    registry = ToolRegistry()

    with pytest.raises(ValueError, match="cannot be empty"):
        registry.register(InvalidTool())
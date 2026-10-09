
import pytest

from tools.calculator import CalculatorTool


@pytest.fixture
def calculator():
    return CalculatorTool()


def test_calculator_multiplies(calculator):
    assert calculator.execute(
        '{"expression": "125 * 48"}'
    ) == "6000"


def test_calculator_respects_operator_precedence(calculator):
    assert calculator.execute(
        '{"expression": "2 + 3 * 4"}'
    ) == "14"


def test_calculator_supports_parentheses(calculator):
    assert calculator.execute(
        '{"expression": "(2 + 3) * 4"}'
    ) == "20"


def test_calculator_divides(calculator):
    assert calculator.execute(
        '{"expression": "10 / 2"}'
    ) == "5.0"


def test_calculator_rejects_function_calls(calculator):
    result = calculator.execute(
        '{"expression": "__import__(\\"os\\").getcwd()"}'
    )

    assert result.startswith("Error:")


def test_calculator_handles_invalid_json(calculator):
    result = calculator.execute("not json")

    assert result.startswith("Error:")


def test_calculator_handles_division_by_zero(calculator):
    result = calculator.execute(
        '{"expression": "1 / 0"}'
    )

    assert result.startswith("Error:")
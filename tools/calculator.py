
import ast
import json
import operator

from tools.base import BaseTool


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "Evaluates basic arithmetic expressions. "
        'Input must be JSON with an "expression" field, '
        'for example {"expression": "125 * 48"}.'
    )

    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def execute(self, tool_input: str) -> str:
        try:
            data = json.loads(tool_input)
            expression = data["expression"]

            if not isinstance(expression, str) or not expression.strip():
                return "Error: expression must be a non-empty string."

            tree = ast.parse(expression, mode="eval")
            result = self._evaluate(tree.body)

            return str(result)

        except (json.JSONDecodeError, KeyError, SyntaxError, TypeError):
            return (
                'Error: provide valid JSON with an "expression" field '
                'containing a basic arithmetic expression.'
            )
        except (ValueError, ZeroDivisionError, OverflowError):
            return "Error: the expression could not be evaluated."
        except ArithmeticError:
            return "Error: arithmetic operation failed."

    def _evaluate(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in self._operators:
            left = self._evaluate(node.left)
            right = self._evaluate(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("Exponent is too large.")

            result = self._operators[type(node.op)](left, right)

            if isinstance(result, (int, float)):
                if abs(result) == float("inf") or result != result:
                    raise ValueError("Non-finite result.")

            return result

        if isinstance(node, ast.UnaryOp) and type(node.op) in self._operators:
            return self._operators[type(node.op)](
                self._evaluate(node.operand)
            )

        raise ValueError("Unsupported expression.")
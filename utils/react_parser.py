from dataclasses import dataclass
from typing import Literal
import re


@dataclass
class ParsedResponse:
    kind: Literal["action", "final"]
    content: str
    tool_name: str | None = None
    tool_input: str | None = None
    thought: str | None = None


def parse_response(response: str) -> ParsedResponse:
    """Parse a ReAct response into an action or a final answer."""

    if not response or not response.strip():
        raise ValueError("The model returned an empty response.")

    response = re.sub(r"<channel\|>+", "", response)

    lines = response.strip().splitlines()

    for index, line in enumerate(lines):
        if line.strip().startswith("Final Answer:"):
            answer = line.strip().partition(":")[2].strip()
            remaining_lines = [
                item.strip()
                for item in lines[index + 1:]
                if item.strip()
            ]

            if remaining_lines:
                answer += "\n" + "\n".join(remaining_lines)

            if not answer:
                raise ValueError("The final answer cannot be empty.")

            return ParsedResponse(
                kind="final",
                content=answer,
            )

    thought = None

    for line in lines:
        if line.strip().startswith("Thought:"):
            thought = line.strip().partition(":")[2].strip()
            break

    for line in lines:
        stripped_line = line.strip()

        if stripped_line.startswith("Action:"):
            action = stripped_line.partition(":")[2].strip()
            tool_name, separator, tool_input = action.partition(":")

            tool_name = tool_name.strip()
            tool_input = tool_input.strip()

            if not separator or not tool_name or not tool_input:
                raise ValueError("The action format is invalid.")

            return ParsedResponse(
                kind="action",
                content=action,
                tool_name=tool_name,
                tool_input=tool_input,
                thought=thought,
            )

    raise ValueError(
        "The response must contain 'Final Answer:' or a valid 'Action:'."
    )
import re
from dataclasses import dataclass
from typing import Literal


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

    # Remove unexpected channel markers before parsing.
    response = re.sub(
        r"<\s*channel\s*\|\s*>",
        "",
        response,
        flags=re.IGNORECASE,
    )

    lines = response.strip().splitlines()

    # Parse an explicit final answer.
    for index, line in enumerate(lines):
        match = re.match(r"^\s*Final Answer\s*:\s*(.*)$", line)

        if match:
            answer_parts = [match.group(1).strip()]
            answer_parts.extend(
                item.strip()
                for item in lines[index + 1:]
                if item.strip()
            )
            answer = "\n".join(part for part in answer_parts if part)

            if not answer:
                raise ValueError("The final answer cannot be empty.")

            return ParsedResponse(
                kind="final",
                content=answer,
            )

    # Extract the thought.
    thought = None

    for line in lines:
        match = re.match(r"^\s*Thought\s*:\s*(.*)$", line)

        if match:
            thought = match.group(1).strip()
            break

    # Parse a tool action.
    for line in lines:
        match = re.match(r"^\s*Action\s*:\s*(.*)$", line)

        if not match:
            continue

        action = match.group(1).strip()
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
        "No valid action or final answer found in the model response."
    )
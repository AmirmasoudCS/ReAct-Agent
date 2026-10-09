from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ParsedResponse:
    """A parsed response from the ReAct model."""

    kind: Literal["action", "final"]
    content: str
    tool_name: str | None = None
    tool_input: str | None = None
    thought: str | None = None


def parse_response(response: str) -> ParsedResponse:
    """Parse a model response into a tool action or final answer."""

    if not response or not response.strip():
        raise ValueError("The model returned an empty response.")

    lines = response.strip().splitlines()

    # Check for a final answer first.
    for index, line in enumerate(lines):
        if line.strip().startswith("Final Answer:"):
            first_line = line.strip().partition(":")[2].strip()
            remaining_lines = lines[index + 1:]
            answer = "\n".join(
                [first_line, *remaining_lines]
            ).strip()

            if not answer:
                raise ValueError("The final answer is empty.")

            return ParsedResponse(
                kind="final",
                content=answer,
            )

    # Extract the model's thought, if present.
    thought = None

    for line in lines:
        if line.strip().startswith("Thought:"):
            thought = line.strip().partition(":")[2].strip()
            break

    # Find the requested tool action.
    for line in lines:
        stripped_line = line.strip()

        if stripped_line.startswith("Action:"):
            action = stripped_line.partition(":")[2].strip()

            tool_name, separator, tool_input = action.partition(":")

            tool_name = tool_name.strip()
            tool_input = tool_input.strip()

            if not separator or not tool_name or not tool_input:
                raise ValueError(
                    "Invalid action format. Expected "
                    "'Action: tool_name: tool_input'."
                )

            return ParsedResponse(
                kind="action",
                content=response.strip(),
                tool_name=tool_name,
                tool_input=tool_input,
                thought=thought,
            )

    raise ValueError(
        "No valid action or final answer found in the model response."
    )

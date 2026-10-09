import re
from dataclasses import dataclass
from typing import Literal

_CHANNEL_RE = re.compile(r"<\s*channel\s*\|\s*>", re.IGNORECASE)
_FINAL_RE = re.compile(r"^\s*Final Answer\s*:\s*(.*)$", re.IGNORECASE)
_THOUGHT_RE = re.compile(r"^\s*Thought\s*:\s*(.*)$", re.IGNORECASE)
_ACTION_RE = re.compile(r"^\s*Action\s*:\s*(.*)$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedResponse:
    kind: Literal["action", "final"]
    content: str
    tool_name: str | None = None
    tool_input: str | None = None
    thought: str | None = None


def parse_response(response: str) -> ParsedResponse:
    """Parse a ReAct response into an action or a final answer.

    Whichever of `Action:` / `Final Answer:` appears first wins.
    """
    if not response or not response.strip():
        raise ValueError("The model returned an empty response.")

    # Newline (not "") so markers glued to text don't merge lines.
    response = _CHANNEL_RE.sub("\n", response)
    lines = response.strip().splitlines()

    thought = None

    for index, line in enumerate(lines):
        if thought is None and (m := _THOUGHT_RE.match(line)):
            thought = m.group(1).strip()
            continue

        if m := _FINAL_RE.match(line):
            answer = "\n".join([m.group(1), *lines[index + 1:]]).strip()
            if not answer:
                raise ValueError("The final answer cannot be empty.")
            return ParsedResponse(kind="final", content=answer, thought=thought)

        if m := _ACTION_RE.match(line):
            action = m.group(1).strip()
            tool_name, sep, tool_input = action.partition(":")
            tool_name, tool_input = tool_name.strip(), tool_input.strip()

            if not sep or not tool_name or not tool_input:
                raise ValueError(
                    "Invalid action format. Expected "
                    "'Action: tool_name: tool_input'."
                )

            return ParsedResponse(
                kind="action",
                content=action,
                tool_name=tool_name,
                tool_input=tool_input,
                thought=thought,
            )

        # Treat an ordinary, non-empty response as a final answer.
        # This allows natural conversational responses such as greetings.
        fallback = "\n".join(
            line for line in lines if line.strip()
        ).strip()

        if fallback:
            return ParsedResponse(
                kind="final",
                content=fallback,
                thought=thought,
            )

        raise ValueError(
            "No valid action or final answer found in the model response."
        )
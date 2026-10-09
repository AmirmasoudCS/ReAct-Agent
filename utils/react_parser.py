import re
from dataclasses import dataclass
from typing import Literal


_CHANNEL_RE = re.compile(r"<\s*channel\s*\|\s*>", re.IGNORECASE)
_FINAL_RE = re.compile(r"^\s*Final Answer\s*:\s*(.*)$", re.IGNORECASE)
_THOUGHT_RE = re.compile(r"^\s*Thought\s*:\s*(.*)$", re.IGNORECASE)
_ACTION_RE = re.compile(r"^\s*Action\s*:\s*(.*)$", re.IGNORECASE)
_PAUSE_RE = re.compile(r"^\s*PAUSE\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedResponse:
    kind: Literal["action", "final"]
    content: str
    tool_name: str | None = None
    tool_input: str | None = None
    thought: str | None = None


def parse_response(response: str) -> ParsedResponse:
    """Parse an LLM response as a tool action or a final answer."""

    if not response or not response.strip():
        raise ValueError("The model returned an empty response.")

    response = _CHANNEL_RE.sub("\n", response)
    lines = response.strip().splitlines()
    thought = None
    has_react_marker = False

    for index, line in enumerate(lines):
        if _THOUGHT_RE.match(line):
            has_react_marker = True
            match = _THOUGHT_RE.match(line)
            if thought is None and match:
                thought = match.group(1).strip()
            continue

        final_match = _FINAL_RE.match(line)
        if final_match:
            answer = "\n".join(
                [final_match.group(1), *lines[index + 1:]]
            ).strip()

            if not answer:
                raise ValueError("The final answer cannot be empty.")

            return ParsedResponse(
                kind="final",
                content=answer,
                thought=thought,
            )

        action_match = _ACTION_RE.match(line)
        if action_match:
            has_react_marker = True
            action = action_match.group(1).strip()
            # Recover when the model mistakenly prefixes its final answer with Action.
            if action.lower().startswith("final answer:"):
                answer = action[len("final answer:"):].strip()

                if not answer:
                    raise ValueError("The final answer cannot be empty.")

                return ParsedResponse(
                    kind="final",
                    content=answer,
                    thought=thought,
                )
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
                content=action,
                tool_name=tool_name,
                tool_input=tool_input,
                thought=thought,
            )

        if _PAUSE_RE.match(line):
            has_react_marker = True

    # Plain conversational replies, such as "Hello!", are valid answers.
    # But malformed ReAct output must not be silently accepted.
    if not has_react_marker:
        return ParsedResponse(
            kind="final",
            content=response.strip(),
        )

    raise ValueError(
        "The model returned an incomplete or invalid ReAct response."
    )
import re
from collections.abc import Iterator
from typing import Any

from llm.client import LLMClient
from prompts.system_prompt import build_system_prompt
from tools.registry import ToolRegistry
from utils.console import (
    print_action,
    print_debug,
    print_error,
    print_observation,
    print_thought,
)
from utils.context_manager import ContextManager
from utils.message import Message
from utils.react_parser import parse_response


# One step of the agent loop, as a plain dict so it serializes to JSON as is:
#   {"type": "token",       "delta": str}                 final-answer text
#   {"type": "action",      "tool_name": str, "tool_input": str}
#   {"type": "observation", "content": str}
#   {"type": "final",       "content": str, "streamed": bool}
#   {"type": "error",       "message": str}
# Every run ends with exactly one "final" or one "error" event.
AgentEvent = dict[str, Any]

# Same markers utils.react_parser understands (kept private to this module).
_CHANNEL_RE = re.compile(r"<\s*channel\s*\|\s*>", re.IGNORECASE)
_FINAL_MARKER_RE = re.compile(
    r"^[ \t]*Final Answer[ \t]*:[ \t]*", re.IGNORECASE | re.MULTILINE
)
_ACTION_LINE_RE = re.compile(
    r"^[ \t]*Action[ \t]*:", re.IGNORECASE | re.MULTILINE
)


class _FinalAnswerStreamer:
    """Find the final answer inside a growing model response.

    A ReAct response is only known to be an answer once the model writes
    "Final Answer:" at the start of a line. Text before that point (the
    thought, or a tool action) must never reach the user, so feed() returns
    an empty string until the marker appears, then the text that follows it.

    Plain replies with no ReAct marker at all are not streamed; they arrive
    in one piece in the final event.
    """

    _PARTIAL_MARKER_WINDOW = 12

    def __init__(self) -> None:
        self._raw = ""
        self._sent = 0
        self._started = False
        self._emitted = False
        self._disabled = False

    def feed(self, delta: str) -> str:
        self._raw += delta
        return self._emit(final=False)

    def flush(self) -> str:
        return self._emit(final=True)

    def _emit(self, final: bool) -> str:
        if self._disabled:
            return ""

        text = _CHANNEL_RE.sub("\n", self._raw)

        if not self._started:
            match = _FINAL_MARKER_RE.search(text)

            if match is None:
                return ""

            # An Action line before the marker wins in parse_response, so
            # this response is a tool call, not an answer.
            if _ACTION_LINE_RE.search(text, 0, match.start()):
                self._disabled = True
                return ""

            self._started = True
            self._sent = match.end()

        end = len(text.rstrip())

        if not final:
            # Hold back a possibly unfinished "<channel|>" marker.
            index = text.rfind("<")

            if (
                index != -1
                and ">" not in text[index:]
                and len(text) - index <= self._PARTIAL_MARKER_WINDOW
            ):
                end = min(end, index)

        if end <= self._sent:
            return ""

        visible = text[self._sent:end]
        self._sent = end

        if not self._emitted:
            visible = visible.lstrip()

            if not visible:
                return ""

            self._emitted = True

        return visible


class ReActAgent:
    def __init__(
        self,
        llm: LLMClient,
        tools: ToolRegistry,
        max_steps: int = 5,
        messages: list[Message] | None = None,
        context_manager: ContextManager | None = None,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")

        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.messages = list(messages) if messages is not None else []
        self.context_manager = context_manager

    def get_messages(self) -> list[dict[str, str]]:
        """Return the complete conversation history for persistence."""
        return [
            {"role": message.role, "content": message.content}
            for message in self.messages
        ]

    def _build_context(
        self,
        system_prompt: str,
    ) -> tuple[str, list[Message]]:
        if self.context_manager is not None:
            return self.context_manager.build_context(
                system_prompt,
                self.messages,
            )

        return system_prompt, self.messages

    def run(self, user_input: str) -> str:
        """Run the agent to completion and return the answer (or error text)."""
        result = ""

        for event in self.run_stream(user_input, stream_tokens=False):
            if event["type"] == "final":
                result = event["content"]
            elif event["type"] == "error":
                result = event["message"]

        return result

    def run_stream(
        self,
        user_input: str,
        stream_tokens: bool = True,
    ) -> Iterator[AgentEvent]:
        """Run the agent, yielding an event for each step as it happens.

        With stream_tokens=True the final answer is also yielded as "token"
        events while the model writes it. With stream_tokens=False the model
        is called without streaming and only step events are produced.
        """
        if not user_input or not user_input.strip():
            raise ValueError("User input cannot be empty.")

        system_prompt = build_system_prompt(
            self.tools.get_descriptions()
        )
        self.messages.append(Message("user", user_input.strip()))

        format_retries = 0

        for _ in range(self.max_steps):
            context_prompt, context_messages = self._build_context(
                system_prompt
            )

            streamed = False

            if stream_tokens:
                streamer = _FinalAnswerStreamer()
                parts: list[str] = []

                for delta in self.llm.stream_response(
                    context_prompt,
                    context_messages,
                ):
                    parts.append(delta)
                    visible = streamer.feed(delta)

                    if visible:
                        streamed = True
                        yield {"type": "token", "delta": visible}

                tail = streamer.flush()

                if tail:
                    streamed = True
                    yield {"type": "token", "delta": tail}

                response = "".join(parts).strip()
            else:
                response = self.llm.generate_response(
                    context_prompt,
                    context_messages,
                )

            print_debug(response)
            self.messages.append(Message("assistant", response))

            try:
                parsed = parse_response(response)
            except ValueError as error:
                print_error(str(error))

                if format_retries >= 1:
                    yield {
                        "type": "error",
                        "message": (
                            "Error: the model repeatedly returned an "
                            "invalid response. Try adjusting the prompt."
                        ),
                    }
                    return

                format_retries += 1
                self.messages.append(
                    Message(
                        "agent_instruction",
                        "Your response format was invalid. Answer with "
                        "'Final Answer: ...' or use the required Action "
                        "format. Do not explain the instructions.",
                    )
                )
                continue

            if parsed.kind == "final":
                yield {
                    "type": "final",
                    "content": parsed.content,
                    "streamed": streamed,
                }
                return

            assert parsed.tool_name is not None
            assert parsed.tool_input is not None

            print_thought(parsed.thought or "")
            print_action(parsed.tool_name, parsed.tool_input)

            yield {
                "type": "action",
                "tool_name": parsed.tool_name,
                "tool_input": parsed.tool_input,
            }

            if self.tools.get(parsed.tool_name) is None:
                observation = (
                    f"Error: tool '{parsed.tool_name}' does not exist. "
                    "Choose a tool from the available tools."
                )
            else:
                observation = self.tools.execute(
                    parsed.tool_name,
                    parsed.tool_input,
                )

            print_observation(observation)

            # Record the observation before yielding it, so the transcript
            # is complete even if the consumer stops reading right here.
            self.messages.append(
                Message("observation", f"Observation: {observation}")
            )
            yield {"type": "observation", "content": observation}

        print_error("The agent reached its maximum number of steps.")

        yield {
            "type": "error",
            "message": (
                "Error: the agent reached its maximum number of steps "
                "without producing a final answer."
            ),
        }
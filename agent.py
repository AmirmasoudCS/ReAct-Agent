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

# How many invalid or empty responses in a row the agent tolerates.
# The counter resets after every valid response.
MAX_FORMAT_RETRIES = 2

INVALID_FORMAT_INSTRUCTION = (
    "Your response format was invalid. Answer with "
    "'Final Answer: ...' or use the required Action "
    "format. Do not explain the instructions."
)
EMPTY_RESPONSE_INSTRUCTION = (
    "Your last response was empty. Read the latest Observation and "
    "reply with either 'Final Answer: ...' or one new "
    "'Thought:' and 'Action:' followed by PAUSE."
)

# Same markers utils.react_parser understands (kept private to this module).
_CHANNEL_RE = re.compile(r"<\s*channel\s*\|\s*>", re.IGNORECASE)
_FINAL_MARKER_RE = re.compile(
    r"^[ \t]*Final Answer[ \t]*:[ \t]*", re.IGNORECASE | re.MULTILINE
)
_ACTION_LINE_RE = re.compile(
    r"^[ \t]*Action[ \t]*:", re.IGNORECASE | re.MULTILINE
)

# A response that opens with one of these is ReAct output; anything else
# is a plain conversational reply and can be streamed right away.
_REACT_START_WORDS = ("thought", "action", "final answer", "pause")
_REACT_START_RE = re.compile(
    r"^(?:thought|action|final answer|pause)\b", re.IGNORECASE
)
# Lines that end a plain reply (the parser would treat them as ReAct).
_STOP_LINE_RE = re.compile(
    r"^[ \t]*(?:Thought[ \t]*:|Action[ \t]*:|PAUSE[ \t]*$)",
    re.IGNORECASE | re.MULTILINE,
)


class _FinalAnswerStreamer:
    """Find the user-visible answer inside a growing model response.

    Two kinds of responses are streamed:

    * ReAct answers: nothing is shown until "Final Answer:" appears at the
      start of a line; then the text after it is streamed. A response with
      an Action line before that marker is a tool call and is never shown.
    * Plain replies: if the response does not open with a ReAct marker
      (Thought / Action / Final Answer / PAUSE), it is a conversational
      reply and is streamed from its first character. If a Thought, Action
      or PAUSE line shows up later, streaming stops at that line.
    """

    _PARTIAL_MARKER_WINDOW = 12

    def __init__(self) -> None:
        self._raw = ""
        self._sent = 0
        self._started = False
        self._plain = False
        self._emitted = False
        self._disabled = False

    def feed(self, delta: str) -> str:
        self._raw += delta
        return self._emit(final=False)

    def flush(self) -> str:
        return self._emit(final=True)

    def _detect_start(self, text: str, final: bool) -> bool:
        """Decide whether visible text has begun. Returns True if so."""
        stripped = text.lstrip()

        if not stripped:
            return False

        lead = len(text) - len(stripped)

        if _REACT_START_RE.match(stripped):
            # ReAct output: wait for the Final Answer marker.
            match = _FINAL_MARKER_RE.search(text)

            if match is None:
                return False

            if _ACTION_LINE_RE.search(text, 0, match.start()):
                self._disabled = True
                return False

            self._started = True
            self._sent = match.end()
            return True

        # Could still turn into a marker word (e.g. "Thou" -> "Thought").
        # Wait for a few more characters before deciding it is plain text.
        lowered = stripped.lower()

        if not final and any(
            word.startswith(lowered) for word in _REACT_START_WORDS
        ):
            return False

        self._started = True
        self._plain = True
        self._sent = lead
        return True

    def _emit(self, final: bool) -> str:
        if self._disabled:
            return ""

        text = _CHANNEL_RE.sub("\n", self._raw)

        if not self._started and not self._detect_start(text, final):
            return ""

        end = len(text.rstrip())

        if self._plain:
            stop = _STOP_LINE_RE.search(text, self._sent)

            if stop is not None:
                end = min(end, stop.start())
                self._disabled = True
                visible = text[self._sent:end].rstrip()
                self._sent = max(self._sent, end)
                return self._finish_visible(visible)

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

        return self._finish_visible(visible)

    def _finish_visible(self, visible: str) -> str:
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

        An empty or badly formatted response is retried (up to
        MAX_FORMAT_RETRIES times in a row). Once a retry succeeds, the
        failed attempts are removed from the history.
        """
        if not user_input or not user_input.strip():
            raise ValueError("User input cannot be empty.")

        system_prompt = build_system_prompt(
            self.tools.get_descriptions()
        )
        self.messages.append(Message("user", user_input.strip()))

        format_retries = 0
        # Index of the first message added by the current retry streak.
        retry_start: int | None = None

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

            is_empty = not response.strip()
            parsed = None
            error_text = ""

            if is_empty:
                # An empty reply is never stored: an empty assistant turn
                # in the history makes the next reply empty as well.
                error_text = "The model returned an empty response."
            else:
                self.messages.append(Message("assistant", response))

                try:
                    parsed = parse_response(response)
                except ValueError as error:
                    error_text = str(error)

            if parsed is None:
                print_error(error_text)

                if format_retries >= MAX_FORMAT_RETRIES:
                    if is_empty:
                        message = (
                            "Error: the model repeatedly returned an "
                            "empty response. Try a larger output limit "
                            "or a different model."
                        )
                    else:
                        message = (
                            "Error: the model repeatedly returned an "
                            "invalid response. Try adjusting the prompt."
                        )

                    yield {"type": "error", "message": message}
                    return

                if retry_start is None:
                    retry_start = len(self.messages) - (
                        0 if is_empty else 1
                    )

                format_retries += 1
                self.messages.append(
                    Message(
                        "agent_instruction",
                        EMPTY_RESPONSE_INSTRUCTION
                        if is_empty
                        else INVALID_FORMAT_INSTRUCTION,
                    )
                )
                continue

            # A valid response ends the retry streak. Drop the failed
            # attempts so they are not sent to the model again.
            if retry_start is not None:
                valid_message = self.messages.pop()
                del self.messages[retry_start:]
                self.messages.append(valid_message)
                retry_start = None

            format_retries = 0

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
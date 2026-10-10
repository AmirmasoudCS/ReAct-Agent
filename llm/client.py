import os
from collections.abc import Iterator
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from utils.message import Message


load_dotenv()


def _debug_enabled() -> bool:
    """Return True when OLLAMA_DEBUG is set to a truthy value."""
    return os.getenv("OLLAMA_DEBUG", "").lower() in {"1", "true", "yes"}


class LLMClient:
    """Client for communicating with a local Ollama model."""

    API_ROLES = {
        "user": "user",
        "assistant": "assistant",
        "observation": "user",
        "agent_instruction": "user",
    }

    def __init__(
        self,
        model: str | None = None,
        client: OpenAI | None = None,
        temperature: float = 0.2,
        top_p: float = 0.9,
        stop: list[str] | None = None,
        max_output_tokens: int = 1024,
    ) -> None:
        if max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive.")

        self.model = model or os.getenv(
            "OLLAMA_MODEL", "gemma4:e4b"
        )
        self.temperature = temperature
        self.top_p = top_p
        self.stop = stop
        self.max_output_tokens = max_output_tokens

        self.client = client or OpenAI(
            base_url=os.getenv(
                "OLLAMA_BASE_URL",
                "http://localhost:11434/v1",
            ),
            api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        )

    def _build_request(
        self,
        system_prompt: str,
        messages: list[Message],
        max_tokens: int | None,
        stop: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build the chat-completion request shared by both call styles.

        stop=None uses the client's default stop sequences. An empty
        list sends no stop sequences at all.
        """
        output_limit = (
            self.max_output_tokens if max_tokens is None else max_tokens
        )

        if output_limit < 1:
            raise ValueError("max_tokens must be positive.")

        conversation = [
            {"role": "system", "content": system_prompt}
        ]

        for message in messages:
            api_role = self.API_ROLES.get(message.role)

            if api_role is None:
                raise ValueError(
                    f"Unsupported internal message role: "
                    f"'{message.role}'."
                )

            conversation.append({
                "role": api_role,
                "content": message.content,
            })

        request: dict[str, Any] = {
            "model": self.model,
            "messages": conversation,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": output_limit,
        }

        stop_sequences = self.stop if stop is None else stop

        if stop_sequences:
            request["stop"] = stop_sequences

        return request

    @staticmethod
    def _log_empty_response(
        request: dict[str, Any],
        finish_reason: str | None,
        reasoning_chars: int,
    ) -> None:
        """Print why a reply was empty (only when OLLAMA_DEBUG is set)."""
        if not _debug_enabled():
            return

        last = request["messages"][-1]

        print(
            "[llm debug] empty response | "
            f"finish_reason={finish_reason!r} | "
            f"reasoning_chars={reasoning_chars} | "
            f"max_tokens={request['max_tokens']} | "
            f"last_message_role={last['role']!r} | "
            f"last_message_tail={last['content'][-200:]!r}"
        )

    def generate_response(
        self,
        system_prompt: str,
        messages: list[Message],
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> str:
        """Send a prompt and conversation history to Ollama."""
        request = self._build_request(
            system_prompt,
            messages,
            max_tokens,
            stop,
        )

        response = self.client.chat.completions.create(**request)

        choice = response.choices[0]
        content = choice.message.content

        if content is None:
            raise ValueError("The model returned an empty response.")

        if not content.strip():
            # Ollama may return thinking text in a separate field.
            reasoning = (
                getattr(choice.message, "reasoning", None)
                or getattr(choice.message, "reasoning_content", None)
                or ""
            )
            self._log_empty_response(
                request,
                choice.finish_reason,
                len(reasoning),
            )

        return content.strip()

    def stream_response(
        self,
        system_prompt: str,
        messages: list[Message],
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Yield the model's response as text fragments as they arrive."""
        request = self._build_request(system_prompt, messages, max_tokens)
        request["stream"] = True

        stream = self.client.chat.completions.create(**request)

        produced = False
        finish_reason = None
        reasoning_chars = 0

        try:
            for chunk in stream:
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]

                if choice.finish_reason:
                    finish_reason = choice.finish_reason

                reasoning = (
                    getattr(choice.delta, "reasoning", None)
                    or getattr(choice.delta, "reasoning_content", None)
                )

                if reasoning:
                    reasoning_chars += len(reasoning)

                delta = choice.delta.content

                if delta:
                    produced = True
                    yield delta
        finally:
            # Runs when the stream ends AND when the consumer stops early,
            # so the connection to Ollama is released either way.
            close = getattr(stream, "close", None)

            if callable(close):
                close()

        if not produced:
            self._log_empty_response(
                request,
                finish_reason,
                reasoning_chars,
            )
import os
from collections.abc import Iterator
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from utils.message import Message


load_dotenv()


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
    ) -> dict[str, Any]:
        """Build the chat-completion request shared by both call styles."""
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

        if self.stop:
            request["stop"] = self.stop

        return request

    def generate_response(
        self,
        system_prompt: str,
        messages: list[Message],
        max_tokens: int | None = None,
    ) -> str:
        """Send a prompt and conversation history to Ollama."""
        request = self._build_request(system_prompt, messages, max_tokens)

        response = self.client.chat.completions.create(**request)

        content = response.choices[0].message.content

        if content is None:
            raise ValueError("The model returned an empty response.")

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

        try:
            for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta.content

                if delta:
                    yield delta
        finally:
            # Runs when the stream ends AND when the consumer stops early,
            # so the connection to Ollama is released either way.
            close = getattr(stream, "close", None)

            if callable(close):
                close()
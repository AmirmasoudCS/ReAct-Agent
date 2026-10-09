import os

from dotenv import load_dotenv
from openai import OpenAI

from utils.message import Message


load_dotenv()


class LLMClient:
    """Client for communicating with a local Ollama model."""

    def __init__(
        self,
        model: str | None = None,
        client: OpenAI | None = None,
        temperature: float = 0.2,
        top_p: float = 0.9,
        stop: list[str] | None = None,
    ) -> None:
        self.model = model or os.getenv(
            "OLLAMA_MODEL", "gemma4:e4b"
        )
        self.temperature = temperature
        self.top_p = top_p
        self.stop = stop

        self.client = client or OpenAI(
            base_url=os.getenv(
                "OLLAMA_BASE_URL",
                "http://localhost:11434/v1",
            ),
            api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        )

    def generate_response(
        self,
        system_prompt: str,
        messages: list[Message],
    ) -> str:
        """Send a prompt and conversation history to Ollama."""

        conversation = [
            {"role": "system", "content": system_prompt}
        ]

        conversation.extend(
            {"role": message.role, "content": message.content}
            for message in messages
        )

        request = {
            "model": self.model,
            "messages": conversation,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }

        if self.stop:
            request["stop"] = self.stop

        response = self.client.chat.completions.create(**request)

        content = response.choices[0].message.content

        if content is None:
            raise ValueError("The model returned an empty response.")

        return content.strip()

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
from utils.message import Message
from utils.react_parser import parse_response


class ReActAgent:
    """A ReAct agent that uses an LLM and registered tools."""

    def __init__(
        self,
        llm: LLMClient,
        tools: ToolRegistry,
        max_steps: int = 5,
        messages: list[Message] | None = None,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")

        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.messages = list(messages) if messages is not None else []

    def get_messages(self) -> list[dict[str, str]]:
        """Return conversation history in a JSON-serializable format."""
        return [
            {"role": message.role, "content": message.content}
            for message in self.messages
        ]

    def run(self, user_input: str) -> str:
        """Process a user request and return the final answer."""

        if not user_input or not user_input.strip():
            raise ValueError("User input cannot be empty.")

        system_prompt = build_system_prompt(
            self.tools.get_descriptions()
        )

        self.messages.append(
            Message("user", user_input.strip())
        )

        format_retries = 0

        for _ in range(self.max_steps):
            response = self.llm.generate_response(
                system_prompt,
                self.messages,
            )

            print_debug(response)

            self.messages.append(
                Message("assistant", response)
            )

            try:
                parsed = parse_response(response)
            except ValueError as error:
                print_error(str(error))

                if format_retries >= 1:
                    return (
                        "Error: the model repeatedly returned an "
                        "invalid response. Try adjusting the prompt."
                    )

                format_retries += 1

                self.messages.append(
                    Message(
                        "user",
                        "Your response format was invalid. "
                        "Answer with 'Final Answer: ...' or use "
                        "the required Action format. "
                        "Do not explain the instructions.",
                    )
                )
                continue

            if parsed.kind == "final":
                return parsed.content

            assert parsed.tool_name is not None
            assert parsed.tool_input is not None

            print_thought(parsed.thought or "")
            print_action(
                parsed.tool_name,
                parsed.tool_input,
            )

            if self.tools.get(parsed.tool_name) is None:
                observation = (
                    f"Error: tool '{parsed.tool_name}' does not "
                    "exist. Choose a tool from the available tools."
                )
            else:
                observation = self.tools.execute(
                    parsed.tool_name,
                    parsed.tool_input,
                )

            print_observation(observation)

            self.messages.append(
                Message("user", f"Observation: {observation}")
            )

        print_error("The agent reached its maximum number of steps.")

        return (
            "Error: the agent reached its maximum number of steps "
            "without producing a final answer."
        )
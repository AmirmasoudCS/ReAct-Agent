from prompts.system_prompt import build_system_prompt
from llm.client import LLMClient
from tools.registry import ToolRegistry
from utils.message import Message
from utils.react_parser import parse_response


class ReActAgent:
    """A ReAct agent that uses an LLM and registered tools."""

    def __init__(
        self,
        llm: LLMClient,
        tools: ToolRegistry,
        max_steps: int = 5,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")

        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.messages: list[Message] = []

    def run(self, user_input: str) -> str:
        """Process a user request and return the final answer."""

        if not user_input or not user_input.strip():
            raise ValueError("User input cannot be empty.")

        system_prompt = build_system_prompt(
            self.tools.get_descriptions()
        )

        self.messages.append(Message("user", user_input.strip()))
        messages = self.messages

        format_retries = 0

        for _ in range(self.max_steps):
            response = self.llm.generate_response(
                system_prompt,
                messages,
            )
            print(f"\n[DEBUG] Raw LLM response:\n{response}\n")

            # Keep the model's response in the conversation history.
            messages.append(Message("assistant", response))

            try:
                parsed = parse_response(response)
            except ValueError:
                if format_retries >= 1:
                    return (
                        "Error: the model repeatedly returned an invalid response. "
                        "Try simplifying the request or adjusting the system prompt."
                    )

                format_retries += 1

                messages.append(
                    Message(
                        "user",
                        "Your response format was invalid. "
                        "Answer with 'Final Answer: ...' or use the required "
                        "Action format. Do not explain the instructions.",
                    )
                )
                continue

            if parsed.kind == "final":
                return parsed.content

            # Check that the requested tool actually exists.
            tool = self.tools.get(parsed.tool_name)

            if tool is None:
                observation = (
                    f"Error: tool '{parsed.tool_name}' does not exist. "
                    "Choose a tool from the available tools."
                )
            else:
                observation = self.tools.execute(
                    parsed.tool_name,
                    parsed.tool_input,
                )

            messages.append(
                Message("user", f"Observation: {observation}")
            )

        return (
            "Error: the agent reached its maximum number of steps "
            "without producing a final answer."
        )
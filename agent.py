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

    def run(self, user_input: str) -> str:
        """Process a user request and return the final answer."""

        if not user_input or not user_input.strip():
            raise ValueError("User input cannot be empty.")

        system_prompt = build_system_prompt(
            self.tools.get_descriptions()
        )

        messages = [Message("user", user_input.strip())]

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
                messages.append(
                    Message(
                        "user",
                        "Your last response could not be parsed. "
                        "If you are finished, use 'Final Answer: ...'. "
                        "Otherwise, use 'Thought: ...', "
                        "'Action: tool_name: tool_input', and 'PAUSE'.",
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
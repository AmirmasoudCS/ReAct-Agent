from agent import ReActAgent
from llm.client import LLMClient
from tools.calculator import CalculatorTool
from tools.wikipedia_search import WikipediaSearchTool
from tools.registry import ToolRegistry
from utils.console import console, print_agent, print_error
from rich.text import Text
from utils.config import load_config


def main() -> None:
    config = load_config()

    tools = ToolRegistry()
    tools.register(CalculatorTool())
    tools.register(WikipediaSearchTool(timeout=config["tools"]["timeout"]))

    llm_config = config["llm"]
    llm = LLMClient(
        model=llm_config["model"],
        temperature=llm_config["temperature"],
        top_p=llm_config["top_p"],
        stop=llm_config["stop"],
    )
    agent = ReActAgent(
        llm=llm,
        tools=tools,
        max_steps=config["agent"]["max_steps"],
    )

    console.print(
        Text(
            "ReAct Agent (type 'exit' to quit)",
            style="bold white",
        )
    )

    while True:
        try:
            user_input = console.input(
                "\n[bold #60A5FA]You: [/bold #60A5FA]"
            ).strip()

            if user_input.lower() == "exit":
                console.print(
                    Text("Goodbye!", style="dim")
                )
                break

            if not user_input:
                continue

            answer = agent.run(user_input)
            print_agent(answer)

        except (KeyboardInterrupt, EOFError):
            console.print(
                Text("\nGoodbye!", style="dim")
            )
            break
        except Exception as error:
            print_error(str(error))


if __name__ == "__main__":
    main()
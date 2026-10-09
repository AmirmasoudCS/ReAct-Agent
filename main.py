from agent import ReActAgent
from llm.client import LLMClient
from tools.calculator import CalculatorTool
from tools.registry import ToolRegistry


def main() -> None:
    tools = ToolRegistry()
    tools.register(CalculatorTool())

    llm = LLMClient()
    agent = ReActAgent(llm=llm, tools=tools)

    print("ReAct Agent (type 'exit' to quit)")

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() == "exit":
            break

        if not user_input:
            continue

        try:
            answer = agent.run(user_input)
            print(f"\nAgent: {answer}")
        except Exception as error:
            print(f"\nError: {error}")


if __name__ == "__main__":
    main()

import argparse

from rich.text import Text

from agent import ReActAgent
from llm.client import LLMClient
from tools.calculator import CalculatorTool
from tools.wikipedia_search import WikipediaSearchTool
from tools.web_search import WebSearchTool
from tools.weather import WeatherTool
from tools.registry import ToolRegistry
from utils.console import console, print_agent, print_error
from utils.config import load_config
from utils.message import Message
from utils.session_manager import SessionManager


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="ReAct Agent with persistent conversation sessions."
    )

    session_group = parser.add_mutually_exclusive_group(required=True)
    session_group.add_argument(
        "-n",
        "--new",
        action="store_true",
        help="Create a new session and start chatting.",
    )
    session_group.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List saved sessions and select one to resume.",
    )
    session_group.add_argument(
        "-sn",
        "--session-name",
        metavar="NAME",
        help="Load a session by its name.",
    )

    return parser.parse_args()


def choose_session(
    session_manager: SessionManager,
) -> dict:
    """Display saved sessions and let the user select one."""
    sessions = session_manager.list_sessions()

    if not sessions:
        raise ValueError(
            "No saved sessions found. Create one with --new."
        )

    console.print("\n[bold]Saved sessions:[/bold]")

    for index, session in enumerate(sessions, start=1):
        console.print(
            f"  [cyan]{index}.[/cyan] "
            f"{session['session_name']} "
            f"[dim](updated: {session['updated_at']}, "
            f"messages: {session['message_count']})[/dim]"
        )

    while True:
        selection = console.input(
            "\n[bold #60A5FA]Select a session number "
            "(or 'q' to quit): [/bold #60A5FA]"
        ).strip()

        if selection.lower() == "q":
            raise SystemExit(0)

        try:
            index = int(selection)
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")
            continue

        if 1 <= index <= len(sessions):
            return session_manager.load_session(
                sessions[index - 1]["session_name"]
            )

        console.print("[red]Selection is out of range.[/red]")


def main() -> None:
    args = parse_args()
    session_manager = SessionManager()

    try:
        if args.new:
            session = session_manager.create_session()
            console.print(
                f"[green]Created session:[/green] "
                f"{session['session_name']}"
            )
        elif args.list:
            session = choose_session(session_manager)
        else:
            session = session_manager.load_session(args.session_name)

        config = load_config()

        tools = ToolRegistry()
        tools.register(CalculatorTool())
        tools.register(
            WikipediaSearchTool(timeout=config["tools"]["timeout"])
        )
        tools.register(
            WebSearchTool(timeout=config["tools"]["timeout"])
        )
        tools.register(
            WeatherTool(timeout=config["tools"]["timeout"])
        )

        llm_config = config["llm"]
        llm = LLMClient(
            model=llm_config["model"],
            temperature=llm_config["temperature"],
            top_p=llm_config["top_p"],
            stop=llm_config["stop"],
        )

        messages = [
            Message(item["role"], item["content"])
            for item in session["messages"]
        ]

        agent = ReActAgent(
            llm=llm,
            tools=tools,
            max_steps=config["agent"]["max_steps"],
            messages=messages,
        )

        session_name = session["session_name"]

        console.print(
            Text(
                f"ReAct Agent | Session: {session_name} "
                "(type 'exit' to quit)",
                style="bold white",
            )
        )

        while True:
            try:
                user_input = console.input(
                    "\n[bold #60A5FA]You: [/bold #60A5FA]"
                ).strip()

                if user_input.lower() == "exit":
                    console.print(Text("Goodbye!", style="dim"))
                    break

                if not user_input:
                    continue

                answer = agent.run(user_input)
                print_agent(answer)

                session_manager.save_session(
                    session_name,
                    agent.get_messages(),
                )

            except (KeyboardInterrupt, EOFError):
                console.print(Text("\nGoodbye!", style="dim"))
                break
            except Exception as error:
                print_error(str(error))

    except (ValueError, FileNotFoundError, FileExistsError) as error:
        print_error(str(error))


if __name__ == "__main__":
    main()
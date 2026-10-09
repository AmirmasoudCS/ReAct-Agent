import os

from dotenv import load_dotenv
from rich.console import Console
from rich.text import Text


load_dotenv()

console = Console()

DEBUG = os.getenv("DEBUG", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def print_user(message: str) -> None:
    console.print(Text("You:", style="bold #60A5FA"))
    console.print(Text(message, style="#60A5FA"))


def print_agent(message: str) -> None:
    console.print(Text("AGENT", style="bold #4ADE80"))
    console.print(Text(message, style="#4ADE80"))


def print_debug(message: str) -> None:
    if DEBUG:
        console.print(Text("DEBUG", style="bold #F87171"))
        console.print(Text(message, style="#F87171"))


def print_thought(thought: str) -> None:
    if thought:
        console.print(Text("THOUGHT", style="bold #C084FC"))
        console.print(Text(thought, style="#C084FC"))


def print_action(tool_name: str, tool_input: str) -> None:
    console.print(
        Text(f"ACTION -> {tool_name}", style="bold #FBBF24")
    )
    console.print(Text(tool_input, style="#FBBF24"))


def print_observation(observation: str) -> None:
    console.print(Text("OBSERVATION", style="bold #22D3EE"))
    console.print(Text(observation, style="#22D3EE"))


def print_error(message: str) -> None:
    console.print(Text("ERROR", style="bold #F87171"))
    console.print(Text(message, style="#F87171"))

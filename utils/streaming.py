"""Terminal rendering for ReActAgent.run_stream() events."""

import sys
from collections.abc import Iterable
from typing import Any, TextIO


def render_stream(
    events: Iterable[dict[str, Any]],
    out: TextIO | None = None,
    prefix: str = "",
) -> str:
    """Print agent events as they arrive and return the final text.

    Tool actions and observations are not printed here: the agent already
    reports them through utils.console. This only prints the answer, token
    by token when it was streamed, or in one piece otherwise.
    """
    out = out or sys.stdout
    answer = ""
    prefix_written = False

    def write_prefix() -> None:
        nonlocal prefix_written

        if prefix and not prefix_written:
            out.write(prefix)

        prefix_written = True

    for event in events:
        kind = event["type"]

        if kind == "token":
            write_prefix()
            out.write(event["delta"])
            out.flush()

        elif kind == "final":
            answer = event["content"]

            if event.get("streamed"):
                out.write("\n")
            else:
                write_prefix()
                out.write(f"{answer}\n")

            out.flush()

        elif kind == "error":
            answer = event["message"]
            out.write(f"{answer}\n")
            out.flush()

    return answer
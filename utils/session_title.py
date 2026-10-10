"""Generate short, readable session titles with the LLM.

Shared by the CLI (main.py) and the HTTP API (api.py).
"""

import re

from llm.client import LLMClient
from prompts.session_title_prompt import SESSION_TITLE_PROMPT
from utils.message import Message
from utils.session_manager import SessionManager

MAX_TITLE_LENGTH = 80
# Only the start of a long first message is needed to name a conversation.
MAX_QUERY_CHARS = 2000


def generate_session_title(
    llm: LLMClient,
    first_query: str,
) -> str:
    """Generate a short session title from the user's first query."""
    response = llm.generate_response(
        SESSION_TITLE_PROMPT,
        [Message("user", first_query[:MAX_QUERY_CHARS])],
        max_tokens=40,
    )

    lines = response.strip().splitlines()

    if not lines:
        raise ValueError("The model returned an empty session title.")

    title = lines[0].strip()
    title = title.removeprefix("Title:").strip()
    title = title.strip("\"'` ")
    # Session names are used as identifiers and cannot contain separators.
    title = re.sub(r"[\\/]+", "-", title)
    title = title.rstrip(" .,:;!?")

    if not title:
        raise ValueError("The model returned an empty session title.")

    # Keep titles reasonably short for the CLI and the sidebar.
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH].rsplit(" ", 1)[0].rstrip(" .,:;!?")

    if not title:
        raise ValueError("The model returned an invalid session title.")

    return title


def make_title_unique(
    session_manager: SessionManager,
    title: str,
    session_id: str,
) -> str:
    """Add a numeric suffix when a title is already in use."""
    existing_names = {
        session["session_name"].casefold()
        for session in session_manager.list_sessions()
        if session["session_id"] != session_id
    }

    if title.casefold() not in existing_names:
        return title

    suffix = 2

    while f"{title} ({suffix})".casefold() in existing_names:
        suffix += 1

    return f"{title} ({suffix})"
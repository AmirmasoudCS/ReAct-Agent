
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class SessionManager:
    """Manage persistent ReAct agent sessions stored as JSON files."""

    def __init__(self, sessions_dir: str | Path = "sessions") -> None:
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def _session_path(self, session_name: str) -> Path:
        """Return the path for a session name after validating it."""
        if (
            not session_name
            or session_name in {".", ".."}
            or Path(session_name).name != session_name
            or "/" in session_name
            or "\\" in session_name
        ):
            raise ValueError("Invalid session name.")

        if session_name.endswith(".json"):
            session_name = session_name[:-5]

        if not session_name:
            raise ValueError("Session name cannot be empty.")

        return self.sessions_dir / f"{session_name}.json"

    def create_session(self, session_name: str | None = None) -> dict[str, Any]:
        """Create and return a new, empty session."""
        if session_name is None:
            session_name = datetime.now().strftime("session_%Y%m%d_%H%M%S")

        path = self._session_path(session_name)

        if path.exists():
            raise FileExistsError(
                f"Session '{path.stem}' already exists."
            )

        now = self._timestamp()
        session = {
            "session_name": path.stem,
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }

        self._write_session(path, session)
        return session

    def list_sessions(self) -> list[dict[str, Any]]:
        """Return metadata for all valid saved sessions."""
        sessions = []

        for path in sorted(self.sessions_dir.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as file:
                    data = json.load(file)

                if not isinstance(data, dict):
                    continue

                messages = data.get("messages")
                if not isinstance(messages, list):
                    continue

                sessions.append({
                    "session_name": data.get("session_name", path.stem),
                    "created_at": data.get("created_at", "Unknown"),
                    "updated_at": data.get("updated_at", "Unknown"),
                    "message_count": len(messages),
                })
            except (OSError, json.JSONDecodeError):
                # Skip invalid files instead of preventing other
                # sessions from being listed.
                continue

        return sessions

    def load_session(self, session_name: str) -> dict[str, Any]:
        """Load a session from disk."""
        path = self._session_path(session_name)

        if not path.exists():
            raise FileNotFoundError(
                f"Session '{path.stem}' was not found."
            )

        try:
            with path.open("r", encoding="utf-8") as file:
                session = json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Session '{path.stem}' contains invalid JSON."
            ) from error

        if not isinstance(session, dict):
            raise ValueError("Invalid session format.")

        messages = session.get("messages")
        if not isinstance(messages, list):
            raise ValueError("Session messages must be a list.")

        for message in messages:
            if (
                not isinstance(message, dict)
                or not isinstance(message.get("role"), str)
                or not isinstance(message.get("content"), str)
            ):
                raise ValueError("Session contains an invalid message.")

        session["session_name"] = path.stem
        return session

    def save_session(
        self,
        session_name: str,
        messages: list[dict[str, str]],
    ) -> None:
        """Update an existing session with its current messages."""
        path = self._session_path(session_name)

        if not path.exists():
            raise FileNotFoundError(
                f"Session '{path.stem}' was not found."
            )

        session = self.load_session(path.stem)
        session["messages"] = messages
        session["updated_at"] = self._timestamp()

        self._write_session(path, session)

    @staticmethod
    def _write_session(
        path: Path,
        session: dict[str, Any],
    ) -> None:
        """Write JSON atomically to avoid partially written sessions."""
        temporary_path = path.with_suffix(".tmp")

        try:
            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(
                    session,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )
                file.write("\n")

            temporary_path.replace(path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
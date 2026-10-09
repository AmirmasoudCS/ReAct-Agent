
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class SessionManager:
    """Manage persistent ReAct sessions using separate transcript and summary files."""

    SUMMARY_FILENAME = "summary.json"
    CONVERSATION_FILENAME = "full_conversation.json"

    def __init__(self, sessions_dir: str | Path = "sessions") -> None:
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    @staticmethod
    def _validate_session_name(session_name: str) -> str:
        """Validate and normalize a session name."""
        if not isinstance(session_name, str) or not session_name.strip():
            raise ValueError("Session name cannot be empty.")

        session_name = session_name.strip()

        if (
            session_name in {".", ".."}
            or Path(session_name).name != session_name
            or "/" in session_name
            or "\\" in session_name
        ):
            raise ValueError("Invalid session name.")

        if session_name.endswith(".json"):
            session_name = session_name[:-5]

        if not session_name or session_name in {".", ".."}:
            raise ValueError("Invalid session name.")

        if "/" in session_name or "\\" in session_name:
            raise ValueError("Invalid session name.")

        return session_name

    def _session_dir(self, session_name: str) -> Path:
        """Return the directory for a validated session name."""
        return self.sessions_dir / self._validate_session_name(session_name)

    def _conversation_path(self, session_name: str) -> Path:
        return self._session_dir(session_name) / self.CONVERSATION_FILENAME

    def _summary_path(self, session_name: str) -> Path:
        return self._session_dir(session_name) / self.SUMMARY_FILENAME

    def _legacy_session_path(self, session_name: str) -> Path:
        return self.sessions_dir / f"{self._validate_session_name(session_name)}.json"

    def create_session(self, session_name: str | None = None) -> dict[str, Any]:
        """Create a new session directory with transcript and summary files."""
        if session_name is None:
            session_name = datetime.now().strftime("session_%Y%m%d_%H%M%S")

        name = self._validate_session_name(session_name)
        session_dir = self.sessions_dir / name
        legacy_path = self.sessions_dir / f"{name}.json"

        if session_dir.exists() or legacy_path.exists():
            raise FileExistsError(f"Session '{name}' already exists.")

        now = self._timestamp()
        session = {
            "session_name": name,
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
        summary = {
            "summary": "",
            "compacted_through_turn": 0,
            "updated_at": None,
        }

        session_dir.mkdir(parents=False, exist_ok=False)
        try:
            self._write_json(session_dir / self.CONVERSATION_FILENAME, session)
            self._write_json(session_dir / self.SUMMARY_FILENAME, summary)
        except Exception:
            for child in session_dir.iterdir():
                child.unlink()
            session_dir.rmdir()
            raise

        return session

    def list_sessions(self) -> list[dict[str, Any]]:
        """Return metadata for valid new-format and legacy sessions."""
        sessions: list[dict[str, Any]] = []

        # Find sessions stored in directories.
        for session_dir in sorted(
            path for path in self.sessions_dir.iterdir() if path.is_dir()
        ):
            conversation_path = session_dir / self.CONVERSATION_FILENAME
            if not conversation_path.is_file():
                continue

            try:
                data = self._read_json(conversation_path)
                messages = data.get("messages") if isinstance(data, dict) else None
                if not isinstance(messages, list):
                    continue

                sessions.append({
                    "session_name": data.get("session_name", session_dir.name),
                    "created_at": data.get("created_at", "Unknown"),
                    "updated_at": data.get("updated_at", "Unknown"),
                    "message_count": len(messages),
                })
            except (OSError, ValueError):
                continue

        # Keep legacy sessions visible until they are migrated.
        for path in sorted(self.sessions_dir.glob("*.json")):
            try:
                data = self._read_json(path)
                if not isinstance(data, dict) or not isinstance(
                    data.get("messages"), list
                ):
                    continue

                # Prefer the directory-based version if both exist.
                if (self.sessions_dir / path.stem).is_dir():
                    continue

                sessions.append({
                    "session_name": data.get("session_name", path.stem),
                    "created_at": data.get("created_at", "Unknown"),
                    "updated_at": data.get("updated_at", "Unknown"),
                    "message_count": len(data["messages"]),
                })
            except (OSError, ValueError):
                continue

        return sorted(sessions, key=lambda item: item["session_name"].lower())

    def load_session(self, session_name: str) -> dict[str, Any]:
        """Load a session and migrate legacy file-based sessions if necessary."""
        name = self._validate_session_name(session_name)
        conversation_path = self._conversation_path(name)

        if conversation_path.is_file():
            session = self._read_session_file(conversation_path, name)
        else:
            legacy_path = self._legacy_session_path(name)
            if not legacy_path.is_file():
                raise FileNotFoundError(f"Session '{name}' was not found.")

            # Validate the legacy session before creating the new structure.
            session = self._read_session_file(legacy_path, name)
            session_dir = self.sessions_dir / name

            if session_dir.exists():
                raise ValueError(
                    f"Session directory '{name}' exists but has no valid "
                    f"'{self.CONVERSATION_FILENAME}'."
                )

            session_dir.mkdir(parents=False, exist_ok=False)
            try:
                self._write_json(conversation_path, session)
                self._write_json(
                    session_dir / self.SUMMARY_FILENAME,
                    {
                        "summary": "",
                        "compacted_through_turn": 0,
                        "updated_at": None,
                    },
                )
            except Exception:
                # Preserve the original file if migration fails.
                if session_dir.exists():
                    for child in session_dir.iterdir():
                        child.unlink()
                    session_dir.rmdir()
                raise

        session["session_name"] = name
        return session

    def save_session(
        self,
        session_name: str,
        messages: list[dict[str, str]],
    ) -> None:
        """Update the full transcript without changing the summary."""
        session = self.load_session(session_name)

        for message in messages:
            if (
                not isinstance(message, dict)
                or not isinstance(message.get("role"), str)
                or not isinstance(message.get("content"), str)
            ):
                raise ValueError("Session contains an invalid message.")

        session["messages"] = messages
        session["updated_at"] = self._timestamp()
        self._write_json(
            self._conversation_path(session["session_name"]),
            session,
        )

    def load_summary(self, session_name: str) -> dict[str, Any]:
        """Load the summary metadata for a session."""
        name = self._validate_session_name(session_name)

        # Ensure a legacy session is migrated first.
        self.load_session(name)
        summary_path = self._summary_path(name)

        if not summary_path.is_file():
            summary = {
                "summary": "",
                "compacted_through_turn": 0,
                "updated_at": None,
            }
            self._write_json(summary_path, summary)
            return summary

        summary = self._read_json(summary_path)
        if not isinstance(summary, dict) or not isinstance(
            summary.get("summary"), str
        ):
            raise ValueError(f"Session '{name}' contains an invalid summary file.")

        summary.setdefault("compacted_through_turn", 0)
        summary.setdefault("updated_at", None)
        return summary

    def save_summary(
        self,
        session_name: str,
        summary: dict[str, Any],
    ) -> None:
        """Save summary data independently from the full transcript."""
        name = self._validate_session_name(session_name)
        self.load_session(name)

        if not isinstance(summary, dict) or not isinstance(
            summary.get("summary"), str
        ):
            raise ValueError(
                "Summary data must be a dictionary with a string 'summary'."
            )

        saved_summary = dict(summary)
        saved_summary.setdefault("compacted_through_turn", 0)
        saved_summary["updated_at"] = self._timestamp()
        self._write_json(self._summary_path(name), saved_summary)

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"File '{path.name}' contains invalid JSON."
            ) from error

    def _read_session_file(
        self,
        path: Path,
        session_name: str,
    ) -> dict[str, Any]:
        session = self._read_json(path)

        if not isinstance(session, dict):
            raise ValueError(f"Session '{session_name}' has an invalid format.")

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

        self._migrate_message_roles(messages)
        session["session_name"] = session_name
        return session

    @staticmethod
    def _migrate_message_roles(messages: list[dict[str, str]]) -> None:
        """Convert legacy observation and retry messages to internal roles."""
        retry_instruction = (
            "Your response format was invalid. "
            "Answer with 'Final Answer: ...' or use "
            "the required Action format. "
            "Do not explain the instructions."
        )

        for message in messages:
            if message["role"] != "user":
                continue

            if message["content"].startswith("Observation: "):
                message["role"] = "observation"
            elif message["content"] == retry_instruction:
                message["role"] = "agent_instruction"

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        """Write JSON atomically to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")

        try:
            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
                file.write("\n")
            temporary_path.replace(path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
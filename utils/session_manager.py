
"""Manage persistent ReAct sessions using separate transcript and summary files."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
import shutil


class SessionManager:
    """Manage persistent sessions with stable IDs and editable display names."""

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
        """Validate and normalize a display name or session identifier."""
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

        return session_name

    def _session_dir(self, session_id: str) -> Path:
        """Return the directory associated with a stable session ID."""
        return self.sessions_dir / self._validate_session_name(session_id)

    def _conversation_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / self.CONVERSATION_FILENAME

    def _summary_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / self.SUMMARY_FILENAME

    def _legacy_session_path(self, session_name: str) -> Path:
        return self.sessions_dir / (
            f"{self._validate_session_name(session_name)}.json"
        )

    def _find_session_dir(self, identifier: str) -> Path | None:
        """Find a session directory by its stable ID or display name."""
        name = self._validate_session_name(identifier)
        direct_path = self.sessions_dir / name

        if (direct_path / self.CONVERSATION_FILENAME).is_file():
            return direct_path

        matches: list[Path] = []

        for directory in self.sessions_dir.iterdir():
            if not directory.is_dir():
                continue

            conversation_path = directory / self.CONVERSATION_FILENAME
            if not conversation_path.is_file():
                continue

            try:
                data = self._read_json(conversation_path)
            except (OSError, ValueError):
                continue

            if isinstance(data, dict) and (
                data.get("session_name") == name
                or data.get("session_id") == name
            ):
                matches.append(directory)

        if len(matches) > 1:
            raise ValueError(
                f"Multiple sessions match '{name}'. "
                "Use the session ID or select a session from --list."
            )

        return matches[0] if matches else None

    def _ensure_unique_display_name(
        self,
        session_name: str,
        exclude_session_id: str | None = None,
    ) -> None:
        """Prevent two sessions from having the same display name."""
        normalized = session_name.casefold()

        for session in self.list_sessions():
            if session["session_id"] == exclude_session_id:
                continue

            if session["session_name"].casefold() == normalized:
                raise ValueError(
                    f"A session named '{session_name}' already exists."
                )

    def create_session(
        self,
        session_name: str | None = None,
    ) -> dict[str, Any]:
        """Create a session with a stable ID independent of its display name."""
        now = self._timestamp()
        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        display_name = self._validate_session_name(
            session_name or session_id
        )

        self._ensure_unique_display_name(display_name)

        session_dir = self._session_dir(session_id)
        legacy_path = self._legacy_session_path(session_id)

        if session_dir.exists() or legacy_path.exists():
            raise FileExistsError(
                f"Session ID '{session_id}' already exists. Try again."
            )

        session = {
            "session_id": session_id,
            "session_name": display_name,
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
            self._write_json(
                session_dir / self.CONVERSATION_FILENAME,
                session,
            )
            self._write_json(
                session_dir / self.SUMMARY_FILENAME,
                summary,
            )
        except Exception:
            for child in session_dir.iterdir():
                child.unlink()
            session_dir.rmdir()
            raise

        return session

    def list_sessions(self) -> list[dict[str, Any]]:
        """List sessions stored in the new directory format and legacy format."""
        sessions: list[dict[str, Any]] = []

        for session_dir in sorted(
            path for path in self.sessions_dir.iterdir() if path.is_dir()
        ):
            conversation_path = session_dir / self.CONVERSATION_FILENAME

            if not conversation_path.is_file():
                continue

            try:
                data = self._read_json(conversation_path)
                if not isinstance(data, dict):
                    continue

                messages = data.get("messages")
                if not isinstance(messages, list):
                    continue

                sessions.append({
                    "session_id": data.get("session_id", session_dir.name),
                    "session_name": data.get(
                        "session_name", session_dir.name
                    ),
                    "created_at": data.get("created_at", "Unknown"),
                    "updated_at": data.get("updated_at", "Unknown"),
                    "message_count": len(messages),
                })
            except (OSError, ValueError):
                continue

        # Keep legacy file-based sessions visible until they are migrated.
        for path in sorted(self.sessions_dir.glob("*.json")):
            try:
                data = self._read_json(path)
                if not isinstance(data, dict):
                    continue

                messages = data.get("messages")
                if not isinstance(messages, list):
                    continue

                if (self.sessions_dir / path.stem).is_dir():
                    continue

                sessions.append({
                    "session_id": data.get("session_id", path.stem),
                    "session_name": data.get("session_name", path.stem),
                    "created_at": data.get("created_at", "Unknown"),
                    "updated_at": data.get("updated_at", "Unknown"),
                    "message_count": len(messages),
                })
            except (OSError, ValueError):
                continue

        return sorted(
            sessions,
            key=lambda item: item["session_name"].casefold(),
        )

    def load_session(self, session_name: str) -> dict[str, Any]:
        """Load a session by display name or stable ID, migrating legacy files."""
        name = self._validate_session_name(session_name)
        session_dir = self._find_session_dir(name)

        if session_dir is not None:
            session = self._read_session_file(
                session_dir / self.CONVERSATION_FILENAME,
                session_dir.name,
            )
            session["session_id"] = session.get(
                "session_id", session_dir.name
            )
            return session

        legacy_path = self._legacy_session_path(name)
        if not legacy_path.is_file():
            raise FileNotFoundError(f"Session '{name}' was not found.")

        session = self._read_session_file(legacy_path, name)
        session_id = session.get("session_id", name)
        session_dir = self._session_dir(session_id)

        if session_dir.exists():
            raise ValueError(
                f"Session directory '{session_id}' exists but has no valid "
                f"'{self.CONVERSATION_FILENAME}'."
            )

        session["session_id"] = session_id
        session_dir.mkdir(parents=False, exist_ok=False)

        try:
            self._write_json(
                session_dir / self.CONVERSATION_FILENAME,
                session,
            )
            self._write_json(
                session_dir / self.SUMMARY_FILENAME,
                {
                    "summary": "",
                    "compacted_through_turn": 0,
                    "updated_at": None,
                },
            )
        except Exception:
            if session_dir.exists():
                for child in session_dir.iterdir():
                    child.unlink()
                session_dir.rmdir()
            raise

        return session

    def rename_session(
        self,
        current_name: str,
        new_name: str,
    ) -> dict[str, Any]:
        """Rename a session without changing its ID or directory."""
        new_name = self._validate_session_name(new_name)
        session = self.load_session(current_name)
        session_id = session["session_id"]

        self._ensure_unique_display_name(
            new_name,
            exclude_session_id=session_id,
        )

        session["session_name"] = new_name
        session["updated_at"] = self._timestamp()

        self._write_json(
            self._conversation_path(session_id),
            session,
        )

        return session

    def remove_session(self, identifier: str) -> dict[str, Any]:
        """Permanently remove a session and its saved files."""
        session = self.load_session(identifier)
        session_id = session["session_id"]
        session_dir = self._session_dir(session_id)

        if not (session_dir / self.CONVERSATION_FILENAME).is_file():
            raise FileNotFoundError(
                f"Session '{identifier}' was not found."
            )

        # Preserve the session metadata for the caller before deleting it.
        removed_session = dict(session)

        # Remove the transcript, summary, and any other files in the directory.
        shutil.rmtree(session_dir)

        # Also remove a legacy file if one remains from an earlier migration.
        legacy_path = self._legacy_session_path(session_id)
        if legacy_path.is_file():
            legacy_path.unlink()

        return removed_session

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
            self._conversation_path(session["session_id"]),
            session,
        )

    def load_summary(self, session_name: str) -> dict[str, Any]:
        """Load summary metadata for a session."""
        session = self.load_session(session_name)
        summary_path = self._summary_path(session["session_id"])

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
            raise ValueError(
                f"Session '{session_name}' contains an invalid summary file."
            )

        summary.setdefault("compacted_through_turn", 0)
        summary.setdefault("updated_at", None)
        return summary

    def save_summary(
        self,
        session_name: str,
        summary: dict[str, Any],
    ) -> None:
        """Save summary data independently from the full transcript."""
        session = self.load_session(session_name)

        if not isinstance(summary, dict) or not isinstance(
            summary.get("summary"), str
        ):
            raise ValueError(
                "Summary data must be a dictionary with a string 'summary'."
            )

        saved_summary = dict(summary)
        saved_summary.setdefault("compacted_through_turn", 0)
        saved_summary["updated_at"] = self._timestamp()

        self._write_json(
            self._summary_path(session["session_id"]),
            saved_summary,
        )

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
            raise ValueError(
                f"Session '{session_name}' has an invalid format."
            )

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
        session.setdefault("session_id", path.parent.name)
        session.setdefault("session_name", session_name)
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

        
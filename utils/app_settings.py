"""Settings the user can change at runtime, stored in settings.json.

config.yaml provides the defaults; settings.json only holds the values the
user changed. Shared by the HTTP API and the CLI.
"""

import json
from pathlib import Path
from typing import Any

SETTINGS_PATH = Path("settings.json")

SETTING_LIMITS: dict[str, dict[str, float]] = {
    "temperature": {"min": 0.0, "max": 1.0, "step": 0.05},
    "max_steps": {"min": 1, "max": 10, "step": 1},
}

MAX_MODEL_NAME_LENGTH = 200


def default_settings(config: dict[str, Any]) -> dict[str, Any]:
    """The values from config.yaml, before any user changes."""
    return {
        "model": config["llm"]["model"],
        "temperature": config["llm"]["temperature"],
        "max_steps": config["agent"]["max_steps"],
    }


def _clean(key: str, value: Any) -> Any:
    """Validate one setting and return its normalized value."""
    if key == "model":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Model must be a non-empty name.")

        name = value.strip()

        if len(name) > MAX_MODEL_NAME_LENGTH:
            raise ValueError("Model name is too long.")

        return name

    if key == "temperature":
        limits = SETTING_LIMITS["temperature"]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Temperature must be a number.")

        if not limits["min"] <= value <= limits["max"]:
            raise ValueError(
                f"Temperature must be between {limits['min']} "
                f"and {limits['max']}."
            )

        return round(float(value), 2)

    if key == "max_steps":
        limits = SETTING_LIMITS["max_steps"]

        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Max steps must be a whole number.")

        if not limits["min"] <= value <= limits["max"]:
            raise ValueError(
                f"Max steps must be between {int(limits['min'])} "
                f"and {int(limits['max'])}."
            )

        return value

    raise ValueError(f"Unknown setting '{key}'.")


def validate_settings(changes: dict[str, Any]) -> dict[str, Any]:
    """Validate a partial update. Raises ValueError on the first problem."""
    return {key: _clean(key, value) for key, value in changes.items()}


def load_settings(
    config: dict[str, Any],
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Defaults from config.yaml with any saved overrides applied.

    A missing or damaged file, or an invalid saved value, falls back to the
    default for that setting instead of stopping the program.
    """
    settings = default_settings(config)
    file_path = SETTINGS_PATH if path is None else Path(path)

    try:
        saved = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings

    if not isinstance(saved, dict):
        return settings

    for key, value in saved.items():
        if key not in settings:
            continue

        try:
            settings[key] = _clean(key, value)
        except ValueError:
            continue

    return settings


def save_settings(
    settings: dict[str, Any],
    path: str | Path | None = None,
) -> None:
    """Write the settings to disk atomically."""
    file_path = SETTINGS_PATH if path is None else Path(path)
    temporary_path = file_path.with_suffix(file_path.suffix + ".tmp")

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(settings, file, indent=2, ensure_ascii=False)
            file.write("\n")
        temporary_path.replace(file_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
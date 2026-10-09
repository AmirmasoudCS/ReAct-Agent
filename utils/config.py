from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

DEFAULTS = {
    "llm": {
        "model": "gemma4:e4b",
        "temperature": 0.2,
        "top_p": 0.9,
        "stop": ["PAUSE", "Observation:"],
    },
    "agent": {"max_steps": 5},
    "tools": {"timeout": 15},
}


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Load config.yaml, filling in defaults for missing values."""
    config = {section: dict(values) for section, values in DEFAULTS.items()}

    if path.exists():
        with open(path, encoding="utf-8") as file:
            loaded = yaml.safe_load(file) or {}

        for section, values in loaded.items():
            if isinstance(values, dict):
                config.setdefault(section, {}).update(values)

    return config
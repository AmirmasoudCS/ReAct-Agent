import json

import pytest

from utils.app_settings import (
    default_settings,
    load_settings,
    save_settings,
    validate_settings,
)

CONFIG = {
    "llm": {"model": "gemma4:e4b", "temperature": 0.2},
    "agent": {"max_steps": 6},
}


def test_defaults_come_from_config():
    assert default_settings(CONFIG) == {
        "model": "gemma4:e4b",
        "temperature": 0.2,
        "max_steps": 6,
    }


def test_missing_file_gives_defaults(tmp_path):
    settings = load_settings(CONFIG, tmp_path / "settings.json")

    assert settings == default_settings(CONFIG)


def test_save_then_load_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    chosen = {"model": "llama3", "temperature": 0.5, "max_steps": 3}

    save_settings(chosen, path)

    assert load_settings(CONFIG, path) == chosen
    assert not path.with_suffix(".json.tmp").exists()


def test_damaged_file_gives_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")

    assert load_settings(CONFIG, path) == default_settings(CONFIG)


def test_invalid_saved_value_falls_back_per_setting(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"model": "llama3", "temperature": 9, "max_steps": 4}),
        encoding="utf-8",
    )

    settings = load_settings(CONFIG, path)

    assert settings["model"] == "llama3"
    assert settings["temperature"] == 0.2
    assert settings["max_steps"] == 4


def test_unknown_saved_keys_are_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"colour": "red"}), encoding="utf-8")

    assert load_settings(CONFIG, path) == default_settings(CONFIG)


def test_validate_normalizes_values():
    cleaned = validate_settings(
        {"model": "  llama3  ", "temperature": 0.3333, "max_steps": 5}
    )

    assert cleaned == {"model": "llama3", "temperature": 0.33, "max_steps": 5}


@pytest.mark.parametrize(
    "changes",
    [
        {"model": ""},
        {"model": 5},
        {"temperature": -0.1},
        {"temperature": 1.5},
        {"temperature": True},
        {"temperature": "0.5"},
        {"max_steps": 0},
        {"max_steps": 11},
        {"max_steps": 2.5},
        {"max_steps": True},
        {"volume": 3},
    ],
)
def test_validate_rejects_bad_values(changes):
    with pytest.raises(ValueError):
        validate_settings(changes)
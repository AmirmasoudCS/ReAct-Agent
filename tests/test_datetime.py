from datetime import datetime, timezone

import pytest

from tools.datetime import DateTimeTool


@pytest.fixture
def tool(monkeypatch):
    """Tool with a fixed clock: 2026-10-10 12:32:05 UTC."""

    fixed_utc = datetime(2026, 10, 10, 12, 32, 5, tzinfo=timezone.utc)

    def fake_now(tz):
        return fixed_utc.astimezone(tz or timezone.utc)

    monkeypatch.setattr(DateTimeTool, "_now", staticmethod(fake_now))

    return DateTimeTool()


def test_default_uses_local_time(tool):
    result = tool.execute("{}")

    assert "Server local time" in result
    assert "ISO 8601: 2026-10-10T12:32:05+00:00" in result


def test_empty_input_is_allowed(tool):
    assert tool.execute("").startswith("Current date and time")


def test_explicit_timezone(tool):
    result = tool.execute('{"timezone": "Europe/Berlin"}')

    assert "Timezone: Europe/Berlin (CEST, UTC+02:00)" in result
    assert "Date: Saturday, 10 October 2026" in result
    assert "Time: 14:32:05" in result
    assert "ISO 8601: 2026-10-10T14:32:05+02:00" in result


def test_unknown_timezone(tool):
    result = tool.execute('{"timezone": "Mars/Olympus"}')

    assert result.startswith("Error: unknown timezone")


def test_non_string_timezone(tool):
    result = tool.execute('{"timezone": 5}')

    assert result == "Error: 'timezone' must be a non-empty string."


def test_blank_timezone(tool):
    result = tool.execute('{"timezone": "  "}')

    assert result == "Error: 'timezone' must be a non-empty string."


def test_invalid_json(tool):
    assert tool.execute("{not json").startswith("Error: invalid JSON")


def test_input_must_be_object(tool):
    assert tool.execute("[1, 2]") == "Error: input must be a JSON object."


def test_missing_timezone_database(tool, monkeypatch):
    monkeypatch.setattr(
        "tools.datetime_tool.available_timezones",
        lambda: set(),
    )

    result = tool.execute('{"timezone": "Mars/Olympus"}')

    assert "pip install tzdata" in result
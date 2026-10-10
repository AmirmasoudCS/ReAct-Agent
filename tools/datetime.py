import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tools.base import BaseTool


class DateTimeTool(BaseTool):
    """Report the current date and time, optionally in a given timezone."""

    name = "datetime"
    description = (
        "Gets the current date, time, and day of the week. "
        'Input JSON: {"timezone": "Europe/Berlin"}. '
        "Timezone is optional and must be an IANA timezone name "
        '(for example "America/New_York" or "Asia/Tokyo"). '
        "If omitted, the server's local time is used. "
        "An empty JSON object {} is valid. Returns the date, time, "
        "timezone, UTC offset, and an ISO 8601 timestamp."
    )

    @staticmethod
    def _now(tz: ZoneInfo | None) -> datetime:
        if tz is None:
            return datetime.now().astimezone()

        return datetime.now(tz)

    @staticmethod
    def _format_offset(now: datetime) -> str:
        offset = now.utcoffset()

        if offset is None:
            return "UTC"

        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        hours, minutes = divmod(abs(total_minutes), 60)

        return f"UTC{sign}{hours:02d}:{minutes:02d}"

    def execute(self, tool_input: str) -> str:
        tool_input = tool_input.strip()

        if not tool_input:
            data = {}
        else:
            try:
                data = json.loads(tool_input)
            except json.JSONDecodeError as error:
                return f"Error: invalid JSON input: {error.msg}."

        if not isinstance(data, dict):
            return "Error: input must be a JSON object."

        timezone = data.get("timezone")
        tz = None

        if timezone is not None:
            if not isinstance(timezone, str) or not timezone.strip():
                return "Error: 'timezone' must be a non-empty string."

            try:
                tz = ZoneInfo(timezone.strip())
            except (ZoneInfoNotFoundError, ValueError, OSError):
                return (
                    f"Error: unknown timezone '{timezone.strip()}'. "
                    "Use an IANA name such as 'Europe/Berlin'."
                )

        now = self._now(tz)

        if tz is None:
            zone_label = "Server local time"
        else:
            zone_label = timezone.strip()

        return "\n".join(
            [
                "Current date and time",
                (
                    f"Timezone: {zone_label} "
                    f"({now.tzname()}, {self._format_offset(now)})"
                ),
                f"Date: {now:%A}, {now.day} {now:%B %Y}",
                f"Time: {now:%H:%M:%S}",
                f"ISO 8601: {now.isoformat(timespec='seconds')}",
            ]
        )
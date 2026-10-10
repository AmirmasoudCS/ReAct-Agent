import json

import requests

from tools.base import BaseTool


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherTool(BaseTool):
    """Retrieve current weather and forecasts for a location."""

    name = "weather"
    description = (
        "Gets current weather conditions and a daily forecast "
        "for a city or location using Open-Meteo. "
        'Input JSON: {"location": "Berlin", "days": 3, '
        '"units": "celsius"}. '
        "Location is required and should be a city name. Days is "
        "optional and must be an integer from 1 to 7, defaulting to 1 "
        "(today only). Use 2 to include tomorrow. "
        'Units is optional: "celsius" or "fahrenheit". '
        "Defaults to celsius. Returns temperatures, conditions, "
        "precipitation, wind, and sunrise/sunset when available."
    )

    def __init__(self, timeout: int = 15) -> None:
        if timeout < 1:
            raise ValueError("Timeout must be at least 1 second.")

        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ReAct-Agent/0.1",
                "Accept": "application/json",
            }
        )

    @staticmethod
    def _weather_description(code) -> str:
        if isinstance(code, int) and not isinstance(code, bool):
            return WEATHER_CODES.get(code, "Unknown conditions")

        return "Unknown conditions"

    @staticmethod
    def _format_value(value, unit: str = "") -> str:
        if value is None:
            return "Unavailable"

        return f"{value}{unit}"

    def _get_location(self, location: str) -> dict | None:
        response = self.session.get(
            GEOCODING_URL,
            params={
                "name": location,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected geocoding response.")

        results = data.get("results", [])

        if not isinstance(results, list):
            raise ValueError("Unexpected geocoding response.")

        if not results:
            return None

        result = results[0]

        if not isinstance(result, dict):
            raise ValueError("Unexpected geocoding result.")

        if not isinstance(result.get("latitude"), (int, float)):
            raise ValueError("Missing location coordinates.")

        if not isinstance(result.get("longitude"), (int, float)):
            raise ValueError("Missing location coordinates.")

        return result

    def _find_place(self, location: str) -> dict | None:
        """Look up a place, retrying with only the part before a comma.

        The geocoder matches place names, not addresses, so
        "Yate, Gloucestershire, England" finds nothing but "Yate" does.
        """
        place = self._get_location(location)

        if place is None and "," in location:
            first_part = location.split(",")[0].strip()

            if first_part:
                place = self._get_location(first_part)

        return place

    def _get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int,
        units: str,
    ) -> dict:
        temperature_unit = (
            "fahrenheit" if units == "fahrenheit" else "celsius"
        )

        response = self.session.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "is_day,"
                    "precipitation,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "daily": (
                    "weather_code,"
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_probability_max,"
                    "precipitation_sum,"
                    "sunrise,"
                    "sunset"
                ),
                "temperature_unit": temperature_unit,
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
                "timezone": "auto",
                "forecast_days": days,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError("Unexpected forecast response.")

        return data

    def _format_forecast(
        self,
        location: dict,
        forecast: dict,
        units: str,
    ) -> str:
        current = forecast.get("current")
        daily = forecast.get("daily")

        if not isinstance(current, dict):
            raise ValueError("Missing current weather data.")

        if not isinstance(daily, dict):
            raise ValueError("Missing daily forecast data.")

        temperature_unit = "°F" if units == "fahrenheit" else "°C"

        wind_unit = "km/h"
        precipitation_unit = "mm"

        location_parts = [
            location.get("name"),
            location.get("admin1"),
            location.get("country"),
        ]

        location_name = ", ".join(
            dict.fromkeys(
                part for part in location_parts
                if isinstance(part, str) and part.strip()
            )
        )

        output = [
            f"Weather for {location_name or 'requested location'}",
            f"Timezone: {forecast.get('timezone', 'Unknown')}",
            "",
            "Current conditions:",
            (
                "Condition: "
                + self._weather_description(
                    current.get("weather_code")
                )
            ),
            (
                "Temperature: "
                + self._format_value(
                    current.get("temperature_2m"),
                    temperature_unit,
                )
            ),
            (
                "Feels like: "
                + self._format_value(
                    current.get("apparent_temperature"),
                    temperature_unit,
                )
            ),
            (
                "Humidity: "
                + self._format_value(
                    current.get("relative_humidity_2m"),
                    "%",
                )
            ),
            (
                "Wind speed: "
                + self._format_value(
                    current.get("wind_speed_10m"),
                    f" {wind_unit}",
                )
            ),
            (
                "Precipitation: "
                + self._format_value(
                    current.get("precipitation"),
                    f" {precipitation_unit}",
                )
            ),
            "",
            "Daily forecast:",
        ]

        dates = daily.get("time", [])

        if not isinstance(dates, list):
            raise ValueError("Unexpected daily forecast data.")

        daily_fields = {
            "weather_code": "Weather code",
            "temperature_2m_max": "Maximum temperature",
            "temperature_2m_min": "Minimum temperature",
            "precipitation_probability_max": "Max precipitation chance",
            "precipitation_sum": "Total precipitation",
            "sunrise": "Sunrise",
            "sunset": "Sunset",
        }

        for index, date in enumerate(dates):
            if not isinstance(date, str):
                continue

            output.append(f"\n{date}:")

            code = self._get_daily_value(
                daily, "weather_code", index
            )
            output.append(
                f"Condition: {self._weather_description(code)}"
            )

            for field, label in daily_fields.items():
                if field == "weather_code":
                    continue

                value = self._get_daily_value(
                    daily, field, index
                )

                if field in {
                    "temperature_2m_max",
                    "temperature_2m_min",
                }:
                    value = self._format_value(
                        value, temperature_unit
                    )
                elif field == "precipitation_probability_max":
                    value = self._format_value(value, "%")
                elif field == "precipitation_sum":
                    value = self._format_value(
                        value, f" {precipitation_unit}"
                    )
                else:
                    value = self._format_value(value)

                output.append(f"{label}: {value}")

        output.append(
            "\nSource: Open-Meteo "
            "(https://open-meteo.com/)"
        )

        return "\n".join(output)

    @staticmethod
    def _get_daily_value(
        daily: dict,
        field: str,
        index: int,
    ):
        values = daily.get(field)

        if not isinstance(values, list) or index >= len(values):
            return None

        return values[index]

    def execute(self, tool_input: str) -> str:
        try:
            data = json.loads(tool_input)
        except json.JSONDecodeError as error:
            return f"Error: invalid JSON input: {error.msg}."

        if not isinstance(data, dict):
            return "Error: input must be a JSON object."

        location = data.get("location")
        days = data.get("days", 1)
        units = data.get("units", "celsius")

        if not isinstance(location, str) or not location.strip():
            return "Error: 'location' must be a non-empty string."

        if (
            not isinstance(days, int)
            or isinstance(days, bool)
            or not 1 <= days <= 7
        ):
            return "Error: 'days' must be an integer from 1 to 7."

        if units not in {"celsius", "fahrenheit"}:
            return (
                "Error: 'units' must be 'celsius' "
                "or 'fahrenheit'."
            )

        try:
            place = self._find_place(location.strip())

            if place is None:
                return (
                    f"Error: could not find a location matching "
                    f"'{location.strip()}'."
                )

            forecast = self._get_forecast(
                latitude=place["latitude"],
                longitude=place["longitude"],
                days=days,
                units=units,
            )

            return self._format_forecast(
                place,
                forecast,
                units,
            )

        except requests.exceptions.Timeout:
            return "Error: weather API request timed out."

        except requests.exceptions.HTTPError as error:
            status = (
                error.response.status_code
                if error.response is not None
                else "unknown"
            )
            return (
                f"Error: weather API returned HTTP {status}. "
                f"Details: {error!r}"
            )

        except requests.exceptions.JSONDecodeError as error:
            return (
                "Error: weather API returned invalid JSON. "
                f"Details: {error!r}"
            )

        except requests.exceptions.RequestException as error:
            return (
                "Error: could not connect to the weather API. "
                f"Details: {error!r}"
            )

        except (ValueError, TypeError, KeyError) as error:
            return (
                "Error: weather API returned an unexpected "
                f"response. Details: {error!r}"
            )
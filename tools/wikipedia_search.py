import json
from urllib.parse import quote

import requests

from tools.base import BaseTool

UNEXPECTED_STRUCTURE_ERROR = (
    "Error: Wikipedia returned an unexpected response structure."
)

DETAIL_LIMITS = {
    "intro": 1200,
    "full": 4000,
}


def _get_query_list(data, key: str) -> list | None:
    """Return data["query"][key] if it is a list, otherwise None."""
    if not isinstance(data, dict):
        return None

    query = data.get("query")
    if not isinstance(query, dict):
        return None

    items = query.get(key)
    if not isinstance(items, list):
        return None

    return items


class WikipediaSearchTool(BaseTool):
    """Search Wikipedia and retrieve article summaries using its API."""

    name = "wikipedia_search"
    description = (
        "Searches Wikipedia and retrieves article text. "
        'Input JSON: {"query": "Alan Turing", "language": "en", '
        '"results": 3, "detail": "intro"}. '
        "Language is optional and defaults to en. Results must be 1 to 5. "
        'Detail is optional: "intro" (default) returns only the article '
        'introduction; "full" returns more of the article, including '
        "sections such as early life, birthplace and career. Use "
        '"full" when the introduction does not contain the fact you need.'
    )

    API_URL = "https://{language}.wikipedia.org/w/api.php"

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "ReAct-Agent/0.1 "
                    "(educational Wikipedia research tool)"
                ),
                "Accept": "application/json",
            }
        )

    def execute(self, tool_input: str) -> str:
        try:
            data = json.loads(tool_input)
        except json.JSONDecodeError as error:
            return f"Error: invalid JSON input: {error.msg}."

        if not isinstance(data, dict):
            return "Error: input must be a JSON object."

        query = data.get("query")
        language = data.get("language", "en")
        result_limit = data.get("results", 3)
        detail = data.get("detail", "intro")

        if not isinstance(query, str) or not query.strip():
            return "Error: 'query' must be a non-empty string."

        if (
            not isinstance(language, str)
            or not language.strip()
            or not language.replace("-", "").isalpha()
        ):
            return "Error: 'language' must be a valid language code."

        if (
            not isinstance(result_limit, int)
            or isinstance(result_limit, bool)
            or not 1 <= result_limit <= 5
        ):
            return "Error: 'results' must be an integer from 1 to 5."

        if not isinstance(detail, str) or detail not in DETAIL_LIMITS:
            return "Error: 'detail' must be \"intro\" or \"full\"."

        language = language.strip().lower()
        query = query.strip()
        api_url = self.API_URL.format(language=language)

        try:
            search_response = self.session.get(
                api_url,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": result_limit,
                    "format": "json",
                    "formatversion": 2,
                },
                timeout=self.timeout,
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            # Validate the structure before treating it as "no results".
            results = _get_query_list(search_data, "search")
            if results is None:
                return UNEXPECTED_STRUCTURE_ERROR

            if not results:
                return f"No Wikipedia articles found for '{query}'."

            # Use the exact page ID returned by the search API.
            selected = results[0]
            if not isinstance(selected, dict):
                return UNEXPECTED_STRUCTURE_ERROR

            page_id = selected["pageid"]
            title = selected["title"]

            summary_params = {
                "action": "query",
                "prop": "extracts",
                "explaintext": 1,
                "exchars": DETAIL_LIMITS[detail],
                "pageids": page_id,
                "format": "json",
                "formatversion": 2,
            }

            # Without exintro, the extract continues past the introduction.
            if detail == "intro":
                summary_params["exintro"] = 1

            summary_response = self.session.get(
                api_url,
                params=summary_params,
                timeout=self.timeout,
            )
            summary_response.raise_for_status()
            summary_data = summary_response.json()

            pages = _get_query_list(summary_data, "pages")
            if pages is None:
                return UNEXPECTED_STRUCTURE_ERROR

            if not pages:
                return f"Error: Wikipedia article '{title}' could not be found."

            page = pages[0]
            if not isinstance(page, dict):
                return UNEXPECTED_STRUCTURE_ERROR

            if "missing" in page:
                return f"Error: Wikipedia article '{title}' could not be found."

            # `or ""` also handles an explicit null extract.
            summary = (page.get("extract") or "").strip()
            if not summary:
                summary = "No introductory summary is available."

            article_url = (
                f"https://{language}.wikipedia.org/wiki/"
                f"{quote(title.replace(' ', '_'), safe='()')}"
            )

            output = [
                f"Article: {title}",
                f"Summary: {summary}",
                f"Source: {article_url}",
            ]

            if len(results) > 1:
                output.append(
                    "Other search results: "
                    + "; ".join(item["title"] for item in results[1:])
                )

            return "\n".join(output)

        except requests.exceptions.JSONDecodeError as error:
            status = (
                error.response.status_code
                if error.response is not None
                else "unknown"
            )
            return (
                "Error: Wikipedia returned invalid JSON. "
                f"HTTP status: {status}. Details: {error!r}"
            )
        except requests.exceptions.Timeout:
            return "Error: Wikipedia request timed out."
        except requests.exceptions.HTTPError as error:
            status = (
                error.response.status_code
                if error.response is not None
                else "unknown"
            )
            return (
                f"Error: Wikipedia returned HTTP {status}. "
                f"Details: {error!r}"
            )
        except requests.exceptions.RequestException as error:
            return (
                "Error: could not connect to Wikipedia. "
                f"Details: {error!r}"
            )
        except (KeyError, IndexError, TypeError, AttributeError) as error:
            return (
                f"{UNEXPECTED_STRUCTURE_ERROR[:-1]} "
                f"Details: {error!r}"
            )
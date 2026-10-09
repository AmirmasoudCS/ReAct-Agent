
import json

from ddgs import DDGS
from ddgs.exceptions import (
    DDGSException,
    RatelimitException,
    TimeoutException,
)

from tools.base import BaseTool


VALID_TIME_LIMITS = {"d", "w", "m", "y"}


class WebSearchTool(BaseTool):
    """Search the web and return relevant pages with snippets."""

    name = "web_search"
    description = (
        "Searches the web for general information, recent events, "
        "official documentation, and sources beyond Wikipedia. "
        'Input JSON: {"query": "Python documentation", '
        '"results": 5, "region": "us-en", "timelimit": "m"}. '
        "Only query is required. Results must be an integer from "
        "1 to 5. Region defaults to us-en. The optional timelimit "
        "can be d (day), w (week), m (month), or y (year). "
        "Omit timelimit to search without a time restriction. "
        "Each result contains a title, URL, and snippet."
    )

    def __init__(self, timeout: int = 15) -> None:
        if timeout < 1:
            raise ValueError("Timeout must be at least 1 second.")

        self.timeout = timeout

    def execute(self, tool_input: str) -> str:
        try:
            data = json.loads(tool_input)
        except json.JSONDecodeError as error:
            return f"Error: invalid JSON input: {error.msg}."

        if not isinstance(data, dict):
            return "Error: input must be a JSON object."

        query = data.get("query")
        result_limit = data.get("results", 5)
        region = data.get("region", "us-en")
        timelimit = data.get("timelimit")

        if not isinstance(query, str) or not query.strip():
            return "Error: 'query' must be a non-empty string."

        if (
            not isinstance(result_limit, int)
            or isinstance(result_limit, bool)
            or not 1 <= result_limit <= 5
        ):
            return "Error: 'results' must be an integer from 1 to 5."

        if (
            not isinstance(region, str)
            or not region.strip()
            or any(character.isspace() for character in region)
        ):
            return "Error: 'region' must be a non-empty region code."

        if timelimit is not None and timelimit not in VALID_TIME_LIMITS:
            return (
                "Error: 'timelimit' must be d, w, m, or y, "
                "or omitted."
            )

        query = query.strip()
        region = region.strip().lower()

        try:
            with DDGS(timeout=self.timeout) as ddgs:
                results = ddgs.text(
                    query,
                    region=region,
                    max_results=result_limit,
                    timelimit=timelimit,
                )

            if not results:
                return f"No web search results found for '{query}'."

            output = [f"Web search results for: {query}"]

            for index, result in enumerate(results, start=1):
                if not isinstance(result, dict):
                    continue

                title = result.get("title")
                url = result.get("href")
                snippet = result.get("body")

                # Ignore malformed entries instead of inventing details.
                if not isinstance(title, str) or not title.strip():
                    continue

                if not isinstance(url, str) or not url.strip():
                    continue

                if not isinstance(snippet, str):
                    snippet = "No snippet available."

                output.append(
                    f"\n{index}. {title.strip()}\n"
                    f"URL: {url.strip()}\n"
                    f"Snippet: {snippet.strip() or 'No snippet available.'}"
                )

            if len(output) == 1:
                return "Error: web search returned no usable results."

            return "\n".join(output)

        except TimeoutException:
            return "Error: web search request timed out."
        except RatelimitException:
            return (
                "Error: web search rate limit reached. "
                "Try again later."
            )
        except DDGSException as error:
            return (
                "Error: web search failed. "
                f"Details: {error!r}"
            )
        except Exception as error:
            return (
                "Error: unexpected failure during web search. "
                f"Details: {error!r}"
            )
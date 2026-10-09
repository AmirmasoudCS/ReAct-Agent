import json
from urllib.parse import quote

import requests
import wikipedia

from tools.base import BaseTool


class WikipediaSearchTool(BaseTool):
    """Search Wikipedia and retrieve an article summary."""

    name = "wikipedia_search"
    description = (
        "Searches Wikipedia and retrieves a short article summary. "
        'Input JSON: {"query": "Alan Turing", '
        '"language": "en", "results": 3}. '
        "Language is optional and defaults to en. Results must be 1 to 5."
    )

    def execute(self, tool_input: str) -> str:
        # Only catch JSON errors around JSON parsing.
        try:
            data = json.loads(tool_input)
        except json.JSONDecodeError as error:
            return f"Error: invalid JSON input: {error.msg}."

        if not isinstance(data, dict):
            return "Error: input must be a JSON object."

        query = data.get("query")
        language = data.get("language", "en")
        result_limit = data.get("results", 3)

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

        try:
            wikipedia.set_lang(language.strip().lower())

            titles = wikipedia.search(
                query.strip(),
                results=result_limit,
            )

            if not titles:
                return f"No Wikipedia articles found for '{query.strip()}'."

            selected_title = titles[0]

            try:
                summary = wikipedia.summary(
                    selected_title,
                    sentences=3,
                    auto_suggest=False,
                )
            except wikipedia.exceptions.DisambiguationError as error:
                options = "\n".join(
                    f"- {option}" for option in error.options[:5]
                )
                return (
                    f"'{selected_title}' is ambiguous. "
                    f"Choose a more specific article:\n{options}"
                )
            except wikipedia.exceptions.PageError:
                return (
                    f"Error: Wikipedia article '{selected_title}' "
                    "could not be found."
                )

            article_url = (
                "https://"
                + language.strip().lower()
                + ".wikipedia.org/wiki/"
                + quote(selected_title.replace(" ", "_"), safe="()")
            )

            output = [
                f"Article: {selected_title}",
                f"Summary: {summary}",
                f"Source: {article_url}",
            ]

            if len(titles) > 1:
                output.append(
                    "Other search results: " + "; ".join(titles[1:])
                )

            return "\n".join(output)

        except wikipedia.exceptions.HTTPTimeoutError:
            return "Error: Wikipedia request timed out."
        except requests.exceptions.RequestException as error:
            return (
                f"Error: could not connect to Wikipedia.\n"
                f"Exception type: {type(error).__name__}\n"
                f"Details: {error!r}"
            )
        except wikipedia.exceptions.WikipediaException as error:
            return f"Error: Wikipedia request failed: {error}"
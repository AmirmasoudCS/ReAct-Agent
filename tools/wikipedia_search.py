import json

import requests
import wikipedia

from tools.base import BaseTool


class WikipediaSearchTool(BaseTool):
    """Search Wikipedia and retrieve an article summary."""

    name = "wikipedia_search"
    description = (
        "Searches Wikipedia and retrieves a short summary of the "
        "best matching article. Input must be JSON with a required "
        '"query" string and optional "language" string (default "en") '
        'and "results" integer from 1 to 5. Example: '
        '{"query": "Alan Turing", "language": "en", "results": 3}.'
    )

    def execute(self, tool_input: str) -> str:
        try:
            data = json.loads(tool_input)

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
                options = error.options[:5]
                formatted_options = "\n".join(
                    f"- {option}" for option in options
                )

                return (
                    f"'{selected_title}' is ambiguous. "
                    "Choose a more specific article:\n"
                    f"{formatted_options}"
                )
            except wikipedia.exceptions.PageError:
                return (
                    f"Error: the Wikipedia article "
                    f"'{selected_title}' could not be found."
                )

            other_titles = titles[1:]

            output = [
                f"Article: {selected_title}",
                f"Summary: {summary}",
                f"Source: https://en.wikipedia.org/wiki/"
                f"{selected_title.replace(' ', '_')}",
            ]

            if other_titles:
                output.append(
                    "Other search results: "
                    + "; ".join(other_titles)
                )

            return "\n".join(output)

        except json.JSONDecodeError:
            return (
                "Error: provide valid JSON with a 'query' field."
            )
        except wikipedia.exceptions.HTTPTimeoutError:
            return "Error: Wikipedia request timed out."
        except wikipedia.exceptions.WikipediaException as error:
            return f"Error: Wikipedia request failed: {error}"
        except requests.exceptions.RequestException:
            return "Error: could not connect to Wikipedia."
import json
import re
import threading
import time
import xml.etree.ElementTree as ET

import requests

from tools.base import BaseTool

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

DEFAULT_RESULTS = 5
MAX_RESULTS = 5
MAX_ABSTRACT_CHARS = 500
MAX_AUTHORS_SHOWN = 3
SORT_OPTIONS = {
    "date": "submittedDate",
    "relevance": "relevance",
}

UNEXPECTED_STRUCTURE_ERROR = (
    "Error: arXiv returned an unexpected response structure."
)

# Words that make an AND-search too narrow when the model adds them.
_STOPWORDS = {
    "a", "an", "the", "on", "of", "in", "for", "and", "about", "to",
    "latest", "recent", "new", "newest", "paper", "papers", "article",
    "articles", "research", "arxiv",
}
_FIELD_RE = re.compile(r"\b(?:all|ti|au|abs|cat|co|jr|rn|id):", re.IGNORECASE)
_CATEGORY_RE = re.compile(r"^[A-Za-z\-]+(?:\.[A-Za-z\-]+)?$")


def _truncate_text(text: str, limit: int) -> str:
    """Cut text to about `limit` characters, ending on a sentence if possible."""
    if len(text) <= limit:
        return text

    cut = text[:limit]
    boundary = cut.rfind(". ")

    if boundary > limit * 0.6:
        cut = cut[: boundary + 1]

    return cut.rstrip() + " ..."


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _build_search_query(query: str, category: str | None) -> str | None:
    """Turn free text into an arXiv query. Returns None if nothing usable."""
    if _FIELD_RE.search(query):
        # The model used arXiv syntax (ti:, au:, cat:, ...): pass it through.
        search = query.strip()
    else:
        terms = re.findall(r"\w[\w\-]*", query)
        meaningful = [t for t in terms if t.lower() not in _STOPWORDS]
        terms = meaningful or terms

        if not terms:
            return None

        search = " AND ".join(f"all:{term}" for term in terms)

    if category:
        search = f"({search}) AND cat:{category}"

    return search


class ArxivSearchTool(BaseTool):
    """Search arXiv for recent research papers."""

    name = "arxiv_search"
    description = (
        "Searches arXiv for research papers and returns title, authors, "
        "date, link and abstract for each. "
        'Input JSON: {"query": "retrieval augmented generation", '
        '"results": 5, "sort": "date", "category": "cs.CL"}. '
        "Results must be 1 to 5. Sort is optional: \"date\" (default) "
        "returns the newest papers first; \"relevance\" returns the best "
        "matches regardless of age. Category is optional (for example "
        '"cs.CL", "cs.LG", "stat.ML"). Use short topic keywords in '
        "'query', not full sentences."
    )

    API_URL = "https://export.arxiv.org/api/query"
    MIN_INTERVAL_SECONDS = 3.0  # arXiv asks for one request per 3 seconds.

    # Class-level so the limit holds even if the tool is created per request.
    _lock = threading.Lock()
    _last_request = float("-inf")

    def __init__(
        self,
        timeout: int = 15,
        min_interval: float = MIN_INTERVAL_SECONDS,
    ) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "ReAct-Agent/0.1 "
                    "(educational arXiv research tool)"
                ),
            }
        )

    def _wait_for_rate_limit(self) -> None:
        cls = type(self)

        with cls._lock:
            wait = self.min_interval - (time.monotonic() - cls._last_request)

            if wait > 0:
                time.sleep(wait)

            cls._last_request = time.monotonic()

    def execute(self, tool_input: str) -> str:
        try:
            data = json.loads(tool_input)
        except json.JSONDecodeError as error:
            return f"Error: invalid JSON input: {error.msg}."

        if not isinstance(data, dict):
            return "Error: input must be a JSON object."

        query = data.get("query")
        result_limit = data.get("results", DEFAULT_RESULTS)
        sort = data.get("sort", "date")
        category = data.get("category")

        if not isinstance(query, str) or not query.strip():
            return "Error: 'query' must be a non-empty string."

        if (
            not isinstance(result_limit, int)
            or isinstance(result_limit, bool)
            or not 1 <= result_limit <= MAX_RESULTS
        ):
            return f"Error: 'results' must be an integer from 1 to {MAX_RESULTS}."

        if not isinstance(sort, str) or sort not in SORT_OPTIONS:
            return "Error: 'sort' must be \"date\" or \"relevance\"."

        if category is not None:
            if not isinstance(category, str) or not _CATEGORY_RE.match(
                category.strip()
            ):
                return "Error: 'category' must be an arXiv category such as \"cs.CL\"."
            category = category.strip()

        query = query.strip()
        search_query = _build_search_query(query, category)

        if search_query is None:
            return "Error: 'query' contains no searchable words."

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": result_limit,
            "sortBy": SORT_OPTIONS[sort],
            "sortOrder": "descending",
        }

        try:
            self._wait_for_rate_limit()
            response = self.session.get(
                self.API_URL,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            root = ET.fromstring(response.content)

            entries = root.findall("atom:entry", NS)

            if not entries:
                return f"No arXiv papers found for '{query}'."

            # arXiv reports bad queries as a single entry whose id points
            # at /api/errors.
            first_id = _clean(entries[0].findtext("atom:id", "", NS))

            if "/api/errors" in first_id:
                detail = _clean(entries[0].findtext("atom:summary", "", NS))
                return f"Error: arXiv rejected the query. Details: {detail}"

            papers = [self._format_entry(i, e) for i, e in enumerate(entries, 1)]

        except requests.exceptions.Timeout:
            return "Error: arXiv request timed out."
        except requests.exceptions.HTTPError as error:
            status = (
                error.response.status_code
                if error.response is not None
                else "unknown"
            )
            hint = " (rate limited, try again shortly)" if status == 429 else ""
            return f"Error: arXiv returned HTTP {status}{hint}."
        except requests.exceptions.RequestException as error:
            return f"Error: could not connect to arXiv. Details: {error!r}"
        except ET.ParseError as error:
            return f"{UNEXPECTED_STRUCTURE_ERROR[:-1]} Details: {error!r}"
        except (KeyError, IndexError, TypeError, AttributeError) as error:
            return f"{UNEXPECTED_STRUCTURE_ERROR[:-1]} Details: {error!r}"

        order = "newest first" if sort == "date" else "by relevance"
        header = f"arXiv results for '{query}' ({order}):"

        return header + "\n\n" + "\n\n".join(papers)

    @staticmethod
    def _format_entry(index: int, entry: ET.Element) -> str:
        title = _clean(entry.findtext("atom:title", "", NS)) or "(untitled)"
        abstract = _truncate_text(
            _clean(entry.findtext("atom:summary", "", NS)),
            MAX_ABSTRACT_CHARS,
        )
        authors = [
            _clean(a.findtext("atom:name", "", NS))
            for a in entry.findall("atom:author", NS)
        ]
        authors = [a for a in authors if a]
        author_text = ", ".join(authors[:MAX_AUTHORS_SHOWN])

        if len(authors) > MAX_AUTHORS_SHOWN:
            author_text += " et al."

        published = _clean(entry.findtext("atom:published", "", NS))[:10]
        link = _clean(entry.findtext("atom:id", "", NS)).replace(
            "http://", "https://", 1
        )

        primary = entry.find("arxiv:primary_category", NS)
        category = primary.get("term") if primary is not None else None

        lines = [
            f"[{index}] {title}",
            f"Authors: {author_text or 'unknown'}",
            f"Published: {published or 'unknown'}"
            + (f" | Category: {category}" if category else ""),
            f"Link: {link}",
            f"Abstract: {abstract or 'not available'}",
        ]

        return "\n".join(lines)
import json
from collections.abc import Callable

from tools.base import BaseTool
from utils.document_store import DocumentStore, SearchHit

DEFAULT_RESULTS = 4
MAX_RESULTS = 5
# Stays well under agent.MAX_OBSERVATION_CHARS (6000).
MAX_OUTPUT_CHARS = 4000
MAX_LISTED_NAMES = 5


class DocumentSearchTool(BaseTool):
    """Search the documents uploaded to the current conversation."""

    name = "document_search"
    description = "Searches the documents uploaded to this conversation."

    def __init__(
        self,
        store: DocumentStore,
        embed_query: Callable[[str], list[float]],
        embedding_model: str,
    ) -> None:
        self.store = store
        self.embed_query = embed_query
        self.embedding_model = embedding_model

        names = [item["name"] for item in store.list_documents()]
        listed = ", ".join(names[:MAX_LISTED_NAMES])

        if len(names) > MAX_LISTED_NAMES:
            listed += f" and {len(names) - MAX_LISTED_NAMES} more"

        self.description = (
            f"Searches the documents uploaded to this conversation "
            f"({listed}) and returns the most relevant excerpts with file "
            "name and page. "
            'Input JSON: {"query": "revenue in 2023", "results": 4, '
            '"document": "report.pdf"}. '
            "Results must be 1 to 5. Document is optional: use it to "
            "search a single file. Use specific keywords or a short "
            "question as the query. If the excerpts do not contain the "
            "answer, search again with different wording."
        )

    def execute(self, tool_input: str) -> str:
        try:
            data = json.loads(tool_input)
        except json.JSONDecodeError as error:
            return f"Error: invalid JSON input: {error.msg}."

        if not isinstance(data, dict):
            return "Error: input must be a JSON object."

        query = data.get("query")
        limit = data.get("results", DEFAULT_RESULTS)
        document = data.get("document")

        if not isinstance(query, str) or not query.strip():
            return "Error: 'query' must be a non-empty string."

        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= MAX_RESULTS
        ):
            return f"Error: 'results' must be an integer from 1 to {MAX_RESULTS}."

        documents = self.store.list_documents()

        if not documents:
            return "Error: no documents have been uploaded to this conversation."

        document_ids = None

        if document is not None:
            if not isinstance(document, str) or not document.strip():
                return "Error: 'document' must be a file name."

            wanted = document.strip().casefold()
            matches = [
                item for item in documents
                if item["name"].casefold() == wanted
            ] or [
                item for item in documents
                if wanted in item["name"].casefold()
            ]

            if not matches:
                names = ", ".join(item["name"] for item in documents)
                return (
                    f"Error: no uploaded document matches "
                    f"'{document.strip()}'. Available documents: {names}."
                )

            document_ids = {item["id"] for item in matches}

        query = query.strip()

        try:
            vector = self.embed_query(query)
        except Exception as error:
            return f"Error: could not embed the query. Details: {error!r}"

        hits, skipped = self.store.search(
            vector,
            limit,
            self.embedding_model,
            document_ids,
        )

        if not hits:
            if skipped:
                return (
                    "Error: these documents were embedded with a different "
                    f"model or cannot be read: {', '.join(skipped)}. "
                    "They must be uploaded again."
                )

            return f"No relevant excerpts found for '{query}'."

        return self._format(query, hits, skipped)

    @staticmethod
    def _format(query: str, hits: list[SearchHit], skipped: list[str]) -> str:
        header = (
            f"Excerpts from uploaded documents for '{query}' "
            "(most relevant first):"
        )
        output = header
        count = 0

        for number, hit in enumerate(hits, start=1):
            page = f"page {hit.page}, " if hit.page else ""
            block = (
                f"[{number}] {hit.document_name} "
                f"({page}excerpt {hit.chunk_index + 1} of {hit.chunk_count})\n"
                f"{hit.text}"
            )

            # Always keep the best excerpt; drop the rest if they do not fit.
            if count and len(output) + len(block) + 2 > MAX_OUTPUT_CHARS:
                break

            output += "\n\n" + block
            count += 1

        if skipped:
            output += (
                "\n\nNote: not searched (different embedding model or "
                f"unreadable): {', '.join(skipped)}."
            )

        return output
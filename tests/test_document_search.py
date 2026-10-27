import pytest

from tools.document_search import DocumentSearchTool
from utils.document_processing import Chunk
from utils.document_store import DocumentStore

MODEL = "fake-embed"


def fake_embed(text: str) -> list[float]:
    lowered = text.lower()
    return [
        float("cat" in lowered) + 0.01,
        float("dog" in lowered) + 0.01,
        float("fish" in lowered) + 0.01,
    ]


@pytest.fixture
def store(tmp_path):
    store = DocumentStore(tmp_path)
    chunks = [
        Chunk("The cat sat on the mat.", 1),
        Chunk("A dog barked loudly.", 2),
        Chunk("Fish swim in the sea.", None),
    ]
    store.add(
        "pets.txt",
        chunks,
        [fake_embed(chunk.text) for chunk in chunks],
        MODEL,
        size_bytes=100,
        pages=2,
    )
    return store


@pytest.fixture
def tool(store):
    return DocumentSearchTool(store, fake_embed, MODEL)


def test_returns_most_relevant_excerpt_first(tool):
    result = tool.execute('{"query": "cat", "results": 2}')

    assert "[1] pets.txt (page 1, excerpt 1 of 3)" in result
    assert result.index("The cat sat") < result.index("[2]")


def test_excerpt_without_page(tool):
    result = tool.execute('{"query": "fish", "results": 1}')
    assert "[1] pets.txt (excerpt 3 of 3)" in result


def test_document_filter(tool):
    assert "The cat sat" in tool.execute(
        '{"query": "cat", "document": "pets"}'
    )
    assert "no uploaded document matches" in tool.execute(
        '{"query": "cat", "document": "other.pdf"}'
    )


def test_no_documents(tmp_path):
    empty = DocumentSearchTool(DocumentStore(tmp_path / "none"), fake_embed, MODEL)
    assert "no documents" in empty.execute('{"query": "cat"}')


def test_embedding_model_mismatch(store):
    other = DocumentSearchTool(store, fake_embed, "another-model")
    assert "different model" in other.execute('{"query": "cat"}')


def test_description_lists_file_names(tool):
    assert "pets.txt" in tool.get_description()


def test_remove_document(store):
    doc_id = store.list_documents()[0]["id"]

    assert store.remove("../escape") is False
    assert store.remove(doc_id) is True
    assert store.list_documents() == []


def test_embedding_failure_is_reported(store):
    def broken(_text):
        raise RuntimeError("ollama down")

    tool = DocumentSearchTool(store, broken, MODEL)
    assert tool.execute('{"query": "cat"}').startswith("Error: could not embed")


def test_output_is_capped(tmp_path):
    store = DocumentStore(tmp_path)
    chunks = [Chunk("cat " * 375) for _ in range(5)]
    store.add("big.txt", chunks, [fake_embed(c.text) for c in chunks], MODEL)
    tool = DocumentSearchTool(store, fake_embed, MODEL)

    result = tool.execute('{"query": "cat", "results": 5}')

    assert len(result) <= 4000
    assert "[3]" not in result


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "[]",
        '{"query": ""}',
        '{"query": "x", "results": 9}',
        '{"query": "x", "results": true}',
        '{"query": "x", "document": ""}',
    ],
)
def test_invalid_input(tool, payload):
    assert tool.execute(payload).startswith("Error:")
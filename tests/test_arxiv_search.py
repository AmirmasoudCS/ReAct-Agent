import json

import pytest
import requests

from tools.arxiv_search import ArxivSearchTool, _build_search_query

SAMPLE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2601.00001v1</id>
    <published>2026-01-02T10:00:00Z</published>
    <title>A Study of
      Retrieval</title>
    <summary>First sentence. Second sentence.</summary>
    <author><name>Ada One</name></author>
    <author><name>Bob Two</name></author>
    <author><name>Cy Three</name></author>
    <author><name>Di Four</name></author>
    <arxiv:primary_category term="cs.CL"/>
  </entry>
</feed>"""

EMPTY_FEED = b"""<feed xmlns="http://www.w3.org/2005/Atom"></feed>"""

ERROR_FEED = b"""<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/api/errors#bad</id>
    <title>Error</title>
    <summary>malformed query</summary>
  </entry>
</feed>"""


class FakeResponse:
    def __init__(self, content=SAMPLE_FEED, status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)


@pytest.fixture
def tool():
    return ArxivSearchTool(min_interval=0)


def patch_get(monkeypatch, tool, response=None, error=None):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        if error:
            raise error
        return response

    monkeypatch.setattr(tool.session, "get", fake_get)
    return calls


def test_formats_paper(monkeypatch, tool):
    patch_get(monkeypatch, tool, FakeResponse())
    out = tool.execute(json.dumps({"query": "retrieval"}))

    assert "[1] A Study of Retrieval" in out
    assert "Ada One, Bob Two, Cy Three et al." in out
    assert "Published: 2026-01-02 | Category: cs.CL" in out
    assert "Link: https://arxiv.org/abs/2601.00001v1" in out


def test_default_sort_is_newest_first(monkeypatch, tool):
    calls = patch_get(monkeypatch, tool, FakeResponse())
    tool.execute(json.dumps({"query": "retrieval", "results": 2}))

    assert calls[0]["sortBy"] == "submittedDate"
    assert calls[0]["sortOrder"] == "descending"
    assert calls[0]["max_results"] == 2


def test_no_results(monkeypatch, tool):
    patch_get(monkeypatch, tool, FakeResponse(EMPTY_FEED))
    assert "No arXiv papers found" in tool.execute('{"query": "zzz"}')


def test_arxiv_error_entry(monkeypatch, tool):
    patch_get(monkeypatch, tool, FakeResponse(ERROR_FEED))
    assert "rejected the query" in tool.execute('{"query": "x"}')


def test_http_429(monkeypatch, tool):
    patch_get(monkeypatch, tool, FakeResponse(status=429))
    assert "HTTP 429" in tool.execute('{"query": "x"}')


def test_timeout(monkeypatch, tool):
    patch_get(monkeypatch, tool, error=requests.exceptions.Timeout())
    assert "timed out" in tool.execute('{"query": "x"}')


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "[]",
        '{"query": ""}',
        '{"query": "x", "results": 9}',
        '{"query": "x", "results": true}',
        '{"query": "x", "sort": "random"}',
        '{"query": "x", "category": "cs.CL; drop"}',
    ],
)
def test_invalid_input(tool, payload):
    assert tool.execute(payload).startswith("Error:")


def test_query_building():
    assert _build_search_query("latest papers on RAG", None) == "all:RAG"
    assert (
        _build_search_query("graph neural networks", "cs.LG")
        == "(all:graph AND all:neural AND all:networks) AND cat:cs.LG"
    )
    assert _build_search_query("ti:transformer", None) == "ti:transformer"
    assert _build_search_query("latest papers", None) == "all:latest AND all:papers"
import json

import wikipedia

from tools.wikipedia_search import WikipediaSearchTool


def test_search_returns_summary(monkeypatch):
    tool = WikipediaSearchTool()

    monkeypatch.setattr(wikipedia, "set_lang", lambda language: None)
    monkeypatch.setattr(
        wikipedia,
        "search",
        lambda query, results: [
            "Alan Turing",
            "Turing test",
        ],
    )
    monkeypatch.setattr(
        wikipedia,
        "summary",
        lambda title, sentences, auto_suggest: (
            "Alan Turing was a British mathematician."
        ),
    )

    result = tool.execute(
        json.dumps({"query": "Alan Turing"})
    )

    assert "Article: Alan Turing" in result
    assert "British mathematician" in result
    assert "https://en.wikipedia.org/wiki/Alan_Turing" in result
    assert "Turing test" in result


def test_search_returns_message_when_no_results(monkeypatch):
    tool = WikipediaSearchTool()

    monkeypatch.setattr(wikipedia, "set_lang", lambda language: None)
    monkeypatch.setattr(
        wikipedia,
        "search",
        lambda query, results: [],
    )

    result = tool.execute('{"query": "no matching article"}')

    assert "No Wikipedia articles found" in result


def test_search_handles_disambiguation(monkeypatch):
    tool = WikipediaSearchTool()

    monkeypatch.setattr(wikipedia, "set_lang", lambda language: None)
    monkeypatch.setattr(
        wikipedia,
        "search",
        lambda query, results: ["Mercury"],
    )

    def raise_disambiguation(title, sentences, auto_suggest):
        raise wikipedia.exceptions.DisambiguationError(
            title,
            ["Mercury (planet)", "Mercury (element)"],
        )

    monkeypatch.setattr(wikipedia, "summary", raise_disambiguation)

    result = tool.execute('{"query": "Mercury"}')

    assert "ambiguous" in result
    assert "Mercury (planet)" in result
    assert "Mercury (element)" in result


def test_search_uses_requested_language(monkeypatch):
    tool = WikipediaSearchTool()
    selected_languages = []

    monkeypatch.setattr(
        wikipedia,
        "set_lang",
        lambda language: selected_languages.append(language),
    )
    monkeypatch.setattr(
        wikipedia,
        "search",
        lambda query, results: ["Künstliche Intelligenz"],
    )
    monkeypatch.setattr(
        wikipedia,
        "summary",
        lambda title, sentences, auto_suggest: "Deutsche Zusammenfassung.",
    )

    result = tool.execute(
        '{"query": "Künstliche Intelligenz", "language": "de"}'
    )

    assert selected_languages == ["de"]
    assert "Deutsche Zusammenfassung" in result


def test_invalid_json_returns_error():
    result = WikipediaSearchTool().execute("{invalid")

    assert result.startswith("Error:")
    assert "valid JSON" in result


def test_empty_query_returns_error():
    result = WikipediaSearchTool().execute('{"query": "  "}')

    assert result.startswith("Error:")
    assert "'query'" in result


def test_invalid_result_limit_returns_error():
    result = WikipediaSearchTool().execute(
        '{"query": "Python", "results": 10}'
    )

    assert result.startswith("Error:")
    assert "1 to 5" in result


def test_non_object_input_returns_error():
    result = WikipediaSearchTool().execute('["Python"]')

    assert result.startswith("Error:")
    assert "JSON object" in result

import json
from unittest.mock import Mock

import requests

from tools.wikipedia_search import WikipediaSearchTool


def make_response(data, status_code=200):
    """Create a mock HTTP response containing JSON data."""
    response = Mock()
    response.status_code = status_code
    response.headers = {"Content-Type": "application/json"}
    response.json.return_value = data
    response.text = json.dumps(data)
    response.url = "https://en.wikipedia.org/w/api.php"
    response.raise_for_status.return_value = None
    return response


def make_search_data(*articles):
    """Build a MediaWiki search response."""
    return {
        "query": {
            "search": [
                {"pageid": page_id, "title": title}
                for page_id, title in articles
            ]
        }
    }


def make_summary_data(page_id, title, summary):
    """Build a MediaWiki article-extract response."""
    return {
        "query": {
            "pages": [
                {
                    "pageid": page_id,
                    "title": title,
                    "extract": summary,
                }
            ]
        }
    }


def configure_successful_search(monkeypatch, tool, title, page_id, summary):
    """Mock the search and summary API requests."""
    search_response = make_response(
        make_search_data((page_id, title))
    )
    summary_response = make_response(
        make_summary_data(page_id, title, summary)
    )

    responses = [search_response, summary_response]
    get_calls = []

    def mock_get(url, **kwargs):
        get_calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(tool.session, "get", mock_get)

    return get_calls


def test_search_returns_summary_and_source(monkeypatch):
    tool = WikipediaSearchTool()

    get_calls = configure_successful_search(
        monkeypatch,
        tool,
        title="Alan Turing",
        page_id=1208,
        summary="Alan Turing was a British mathematician.",
    )

    result = tool.execute(
        json.dumps({"query": "Alan Turing"})
    )

    assert "Article: Alan Turing" in result
    assert "British mathematician" in result
    assert "https://en.wikipedia.org/wiki/Alan_Turing" in result
    assert len(get_calls) == 2

    search_params = get_calls[0][1]["params"]
    summary_params = get_calls[1][1]["params"]

    assert search_params["action"] == "query"
    assert search_params["list"] == "search"
    assert search_params["srsearch"] == "Alan Turing"
    assert search_params["format"] == "json"

    assert summary_params["action"] == "query"
    assert summary_params["prop"] == "extracts"
    assert summary_params["pageids"] == 1208
    assert summary_params["explaintext"] == 1


def test_search_returns_other_results(monkeypatch):
    tool = WikipediaSearchTool()

    search_response = make_response(
        make_search_data(
            (1208, "Alan Turing"),
            (2000, "Turing test"),
        )
    )
    summary_response = make_response(
        make_summary_data(
            1208,
            "Alan Turing",
            "Alan Turing was a British mathematician.",
        )
    )

    responses = [search_response, summary_response]
    monkeypatch.setattr(
        tool.session,
        "get",
        lambda url, **kwargs: responses.pop(0),
    )

    result = tool.execute(
        '{"query": "Alan Turing", "results": 2}'
    )

    assert "Article: Alan Turing" in result
    assert "Other search results: Turing test" in result


def test_search_returns_message_when_no_results(monkeypatch):
    tool = WikipediaSearchTool()

    monkeypatch.setattr(
        tool.session,
        "get",
        lambda url, **kwargs: make_response(
            {"query": {"search": []}}
        ),
    )

    result = tool.execute('{"query": "no matching article"}')

    assert "No Wikipedia articles found" in result


def test_search_uses_requested_language(monkeypatch):
    tool = WikipediaSearchTool()

    get_calls = configure_successful_search(
        monkeypatch,
        tool,
        title="Künstliche Intelligenz",
        page_id=123,
        summary="Deutsche Zusammenfassung.",
    )

    result = tool.execute(
        '{"query": "Künstliche Intelligenz", "language": "de"}'
    )

    assert "Deutsche Zusammenfassung" in result
    assert "https://de.wikipedia.org/wiki/" in result

    for url, _ in get_calls:
        assert url == "https://de.wikipedia.org/w/api.php"


def test_search_uses_requested_result_limit(monkeypatch):
    tool = WikipediaSearchTool()

    get_calls = configure_successful_search(
        monkeypatch,
        tool,
        title="Python",
        page_id=23862,
        summary="Python is a programming language.",
    )

    tool.execute('{"query": "Python", "results": 2}')

    assert get_calls[0][1]["params"]["srlimit"] == 2


def test_search_handles_missing_article(monkeypatch):
    tool = WikipediaSearchTool()

    search_response = make_response(
        make_search_data((1208, "Alan Turing"))
    )
    summary_response = make_response(
        {
            "query": {
                "pages": [
                    {
                        "pageid": 1208,
                        "title": "Alan Turing",
                        "missing": True,
                    }
                ]
            }
        }
    )

    responses = [search_response, summary_response]
    monkeypatch.setattr(
        tool.session,
        "get",
        lambda url, **kwargs: responses.pop(0),
    )

    result = tool.execute('{"query": "Alan Turing"}')

    assert "could not be found" in result


def test_search_handles_empty_summary(monkeypatch):
    tool = WikipediaSearchTool()

    configure_successful_search(
        monkeypatch,
        tool,
        title="Alan Turing",
        page_id=1208,
        summary="",
    )

    result = tool.execute('{"query": "Alan Turing"}')

    assert "No introductory summary is available" in result


def test_invalid_json_returns_error():
    result = WikipediaSearchTool().execute("{invalid")

    assert result.startswith("Error:")
    assert "invalid JSON" in result


def test_empty_query_returns_error():
    result = WikipediaSearchTool().execute('{"query": "  "}')

    assert result.startswith("Error:")
    assert "'query'" in result


def test_missing_query_returns_error():
    result = WikipediaSearchTool().execute('{"language": "en"}')

    assert result.startswith("Error:")
    assert "'query'" in result


def test_invalid_language_returns_error():
    result = WikipediaSearchTool().execute(
        '{"query": "Python", "language": "!!!"}'
    )

    assert result.startswith("Error:")
    assert "'language'" in result


def test_invalid_result_limit_returns_error():
    result = WikipediaSearchTool().execute(
        '{"query": "Python", "results": 10}'
    )

    assert result.startswith("Error:")
    assert "1 to 5" in result


def test_boolean_result_limit_returns_error():
    result = WikipediaSearchTool().execute(
        '{"query": "Python", "results": true}'
    )

    assert result.startswith("Error:")
    assert "1 to 5" in result


def test_non_object_input_returns_error():
    result = WikipediaSearchTool().execute('["Python"]')

    assert result.startswith("Error:")
    assert "JSON object" in result


def test_search_handles_http_error(monkeypatch):
    tool = WikipediaSearchTool()

    response = Mock()
    response.status_code = 403
    error = requests.exceptions.HTTPError(
        "403 Forbidden",
        response=response,
    )
    response.raise_for_status.side_effect = error

    monkeypatch.setattr(
        tool.session,
        "get",
        lambda url, **kwargs: response,
    )

    result = tool.execute('{"query": "Python"}')

    assert "HTTP 403" in result


def test_search_handles_timeout(monkeypatch):
    tool = WikipediaSearchTool()

    monkeypatch.setattr(
        tool.session,
        "get",
        Mock(side_effect=requests.exceptions.Timeout()),
    )

    result = tool.execute('{"query": "Python"}')

    assert "timed out" in result


def test_search_handles_network_error(monkeypatch):
    tool = WikipediaSearchTool()

    monkeypatch.setattr(
        tool.session,
        "get",
        Mock(
            side_effect=requests.exceptions.ConnectionError(
                "Connection refused"
            )
        ),
    )

    result = tool.execute('{"query": "Python"}')

    assert "could not connect" in result
    assert "ConnectionError" in result


def test_search_handles_invalid_json_response(monkeypatch):
    tool = WikipediaSearchTool()

    response = Mock()
    response.status_code = 200
    response.headers = {"Content-Type": "text/html"}
    response.text = "<html>Unexpected response</html>"
    response.url = "https://en.wikipedia.org/w/api.php"
    response.raise_for_status.return_value = None
    response.json.side_effect = requests.exceptions.JSONDecodeError(
        "Expecting value",
        response.text,
        0,
    )

    monkeypatch.setattr(
        tool.session,
        "get",
        lambda url, **kwargs: response,
    )

    result = tool.execute('{"query": "Python"}')

    assert "invalid JSON" in result


def test_search_handles_unexpected_response_structure(monkeypatch):
    tool = WikipediaSearchTool()

    monkeypatch.setattr(
        tool.session,
        "get",
        lambda url, **kwargs: make_response(
            {"unexpected": "structure"}
        ),
    )

    search_data = search_response.json()

    if (
        not isinstance(search_data, dict)
        or not isinstance(search_data.get("query"), dict)
        or not isinstance(search_data["query"].get("search"), list)
    ):
        return "Error: Wikipedia returned an unexpected response structure."

    results = search_data["query"]["search"]

    assert "unexpected response structure" in result


def test_session_has_user_agent():
    tool = WikipediaSearchTool()

    assert "User-Agent" in tool.session.headers
    assert "ReAct-Agent" in tool.session.headers["User-Agent"]


def test_timeout_is_used():
    tool = WikipediaSearchTool(timeout=7)

    response = make_response(
        make_search_data((1208, "Alan Turing"))
    )
    monkeypatch_calls = []

    def mock_get(url, **kwargs):
        monkeypatch_calls.append(kwargs)
        return response

    tool.session.get = mock_get
    tool.execute('{"query": "Alan Turing"}')

    assert monkeypatch_calls[0]["timeout"] == 7
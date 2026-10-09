import pytest

from utils.react_parser import parse_response


def test_plain_greeting_is_final_answer():
    parsed = parse_response("Hello! How can I help you today?")

    assert parsed.kind == "final"
    assert parsed.content == "Hello! How can I help you today?"


def test_valid_action_is_parsed():
    response = """
Thought: I should search Wikipedia.
Action: wikipedia_search: {"query": "Isaac Newton", "results": 1}
PAUSE
"""
    parsed = parse_response(response)

    assert parsed.kind == "action"
    assert parsed.tool_name == "wikipedia_search"
    assert parsed.tool_input == '{"query": "Isaac Newton", "results": 1}'


def test_channel_markers_do_not_break_action_parsing():
    response = (
        "Thought: I should search.\n"
        "<channel|>Action: wikipedia_search: "
        '{"query": "Isaac Newton", "results": 1}\n'
        "PAUSE"
    )

    parsed = parse_response(response)

    assert parsed.kind == "action"
    assert parsed.tool_name == "wikipedia_search"


def test_malformed_action_is_not_a_final_answer():
    response = "Thought: I should search.\nAction: wikipedia_search\nPAUSE"

    with pytest.raises(ValueError):
        parse_response(response)
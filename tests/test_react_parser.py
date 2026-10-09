import pytest

from utils.react_parser import parse_response


def test_parses_action_with_channel_marker():
    response = (
        'Thought: Search Wikipedia.\n'
        '<channel|>Action: wikipedia_search: '
        '{"query": "Olleselinus birthplace"}\n'
        'PAUSE'
    )
    parsed = parse_response(response)

    assert parsed.kind == "action"
    assert parsed.tool_name == "wikipedia_search"
    assert parsed.tool_input == '{"query": "Olleselinus birthplace"}'
    assert parsed.thought == "Search Wikipedia."


def test_parses_final_answer_with_channel_marker():
    parsed = parse_response(
        '<channel|>Final Answer: I could not find a reliable match.'
    )
    assert parsed.kind == "final"
    assert parsed.content == "I could not find a reliable match."


def test_marker_glued_to_previous_text():
    parsed = parse_response("Thought: hmm<channel|>Action: calc: 2+2")
    assert parsed.kind == "action"
    assert parsed.tool_input == "2+2"


def test_final_answer_preserves_paragraphs_and_indentation():
    parsed = parse_response(
        "Final Answer: Line one\n\nLine two\n    indented"
    )
    assert parsed.content == "Line one\n\nLine two\n    indented"


def test_action_before_hallucinated_final_answer_wins():
    response = (
        "Action: search: cats\n"
        "Observation: made up\n"
        "Final Answer: made up"
    )
    parsed = parse_response(response)
    assert parsed.kind == "action"
    assert parsed.tool_name == "search"


def test_tool_input_may_contain_colons():
    parsed = parse_response("Action: fetch: https://example.com:8080/x")
    assert parsed.tool_input == "https://example.com:8080/x"


@pytest.mark.parametrize("bad", ["", "   \n", "just chatting",
                                 "Action: search", "Action: : foo",
                                 "Final Answer:   "])
def test_invalid_responses_raise(bad):
    with pytest.raises(ValueError):
        parse_response(bad)
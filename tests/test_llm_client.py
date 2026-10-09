
from types import SimpleNamespace

from llm.client import LLMClient
from utils.message import Message


class FakeCompletions:
    def create(self, **kwargs):
        self.kwargs = kwargs

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="  Hello from the model!  "
                    )
                )
            ]
        )


class FakeOpenAI:
    def __init__(self):
        self.chat = SimpleNamespace(
            completions=FakeCompletions()
        )


def test_generate_response_returns_model_text():
    fake_client = FakeOpenAI()
    llm = LLMClient(client=fake_client)

    result = llm.generate_response(
        system_prompt="You are a helpful assistant.",
        messages=[Message("user", "Hello!")],
    )

    assert result == "Hello from the model!"


def test_generate_response_sends_system_and_user_messages():
    fake_client = FakeOpenAI()
    llm = LLMClient(client=fake_client)

    llm.generate_response(
        system_prompt="Follow the ReAct format.",
        messages=[Message("user", "Calculate 2 + 2.")],
    )

    sent_messages = fake_client.chat.completions.kwargs["messages"]

    assert sent_messages[0] == {
        "role": "system",
        "content": "Follow the ReAct format.",
    }
    assert sent_messages[1] == {
        "role": "user",
        "content": "Calculate 2 + 2.",
    }


def test_generate_response_rejects_empty_content():
    fake_client = FakeOpenAI()
    fake_client.chat.completions.create = lambda **kwargs: (
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=None)
                )
            ]
        )
    )

    llm = LLMClient(client=fake_client)

    try:
        llm.generate_response(
            "System prompt",
            [Message("user", "Hello")],
        )
    except ValueError as error:
        assert "empty response" in str(error).lower()
    else:
        raise AssertionError("Expected ValueError")
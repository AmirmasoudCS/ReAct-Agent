from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import ReActAgent
from llm.client import LLMClient
from tools.calculator import CalculatorTool
from tools.registry import ToolRegistry
from tools.weather import WeatherTool
from tools.web_search import WebSearchTool
from tools.wikipedia_search import WikipediaSearchTool
from utils.config import load_config
from utils.context_manager import ContextManager
from utils.message import Message
from utils.session_manager import SessionManager
from utils.react_parser import parse_response


app = FastAPI(
    title="ReAct Agent API",
    description="HTTP API for the ReAct agent and its persistent sessions.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_manager = SessionManager()
config = load_config()


class CreateSessionRequest(BaseModel):
    name: str | None = None


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)


def build_agent(session: dict[str, Any]) -> ReActAgent:
    """Build an agent using the saved transcript for a session."""
    llm_config = config["llm"]
    context_config = config["context"]

    llm = LLMClient(
        model=llm_config["model"],
        temperature=llm_config["temperature"],
        top_p=llm_config["top_p"],
        stop=llm_config["stop"],
        max_output_tokens=context_config["max_output_tokens"],
    )

    tools = ToolRegistry()
    tools.register(CalculatorTool())
    tools.register(
        WikipediaSearchTool(timeout=config["tools"]["timeout"])
    )
    tools.register(
        WebSearchTool(timeout=config["tools"]["timeout"])
    )
    tools.register(
        WeatherTool(timeout=config["tools"]["timeout"])
    )

    messages = [
        Message(item["role"], item["content"])
        for item in session["messages"]
    ]

    context_manager = ContextManager(
        session_manager=session_manager,
        session_name=session["session_id"],
        llm=llm,
        context_config=context_config,
    )

    return ReActAgent(
        llm=llm,
        tools=tools,
        max_steps=config["agent"]["max_steps"],
        messages=messages,
        context_manager=context_manager,
    )


def get_display_messages(
    messages: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Convert the internal ReAct transcript into chat messages."""
    display_messages = []

    for message in messages:
        role = message["role"]
        content = message["content"]

        if role == "user":
            display_messages.append({
                "role": "user",
                "content": content,
            })

        elif role == "assistant":
            try:
                parsed = parse_response(content)
            except ValueError:
                continue

            if parsed.kind == "final":
                display_messages.append({
                    "role": "assistant",
                    "content": parsed.content,
                })

    return display_messages


def serialize_session(
    session: dict[str, Any],
    include_messages: bool = False,
) -> dict[str, Any]:
    """Return a frontend-friendly representation of a session."""
    result = {
        "id": session["session_id"],
        "name": session["session_name"],
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "message_count": len(session.get("messages", [])),
    }

    if include_messages:
        result["messages"] = get_display_messages(
            session.get("messages", [])
        )

    return result


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sessions")
def list_sessions() -> list[dict[str, Any]]:
    sessions = session_manager.list_sessions()

    return [
        {
            "id": session["session_id"],
            "name": session["session_name"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "message_count": session["message_count"],
        }
        for session in sessions
    ]


@app.post("/api/sessions", status_code=201)
def create_session(
    request: CreateSessionRequest,
) -> dict[str, Any]:
    try:
        session = session_manager.create_session(request.name)
    except (ValueError, FileExistsError) as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    return serialize_session(session, include_messages=True)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return serialize_session(session, include_messages=True)


@app.post("/api/sessions/{session_id}/messages")
def send_message(
    session_id: str,
    request: SendMessageRequest,
) -> dict[str, Any]:
    content = request.content.strip()

    if not content:
        raise HTTPException(
            status_code=422,
            detail="Message content cannot be empty.",
        )

    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    try:
        agent = build_agent(session)
        answer = agent.run(content)

        # Persist the full internal transcript, not just visible messages.
        session_manager.save_session(
            session["session_id"],
            agent.get_messages(),
        )

        # Generate a readable display name from the first user message.
        if not session["messages"]:
            proposed_name = " ".join(content.split())[:40]

            try:
                session_manager.rename_session(
                    session["session_id"],
                    proposed_name,
                )
            except ValueError:
                # A duplicate display name must not prevent the response.
                pass

        updated_session = session_manager.load_session(
            session["session_id"]
        )

    except Exception as error:
        # Keep the detailed exception in the backend console.
        print(f"Agent request failed: {error}")
        raise HTTPException(
            status_code=500,
            detail="The agent failed to process this message.",
        ) from error

    return {
        "session": serialize_session(
            updated_session,
            include_messages=False,
        ),
        "messages": get_display_messages(
            agent.get_messages()
        ),
        "answer": answer,
    }
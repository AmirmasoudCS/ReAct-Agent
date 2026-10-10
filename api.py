import json
import threading
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
from utils.session_title import generate_session_title, make_title_unique
from utils.react_parser import parse_response


app = FastAPI(
    title="ReAct Agent API",
    description="HTTP API for the ReAct agent and its persistent sessions.",
    version="1.2.0",
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

BUSY_MESSAGE = (
    "This conversation is busy. Wait for the agent to finish, "
    "or stop it first."
)

# One lock per session. A run holds it from start to finish (including the
# moment after the client disconnects, while the transcript is saved), so a
# new message, a rename, or a delete can never interleave with a save.
_session_locks: dict[str, threading.Lock] = {}
_session_locks_guard = threading.Lock()


def get_session_lock(session_id: str) -> threading.Lock:
    with _session_locks_guard:
        return _session_locks.setdefault(session_id, threading.Lock())


class CreateSessionRequest(BaseModel):
    name: str | None = None


class RenameSessionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


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
) -> list[dict[str, Any]]:
    """Convert the internal transcript into user-facing messages."""
    display_messages: list[dict[str, Any]] = []
    pending_activity: list[dict[str, str]] = []

    for message in messages:
        role = message["role"]
        content = message["content"]

        if role == "user":
            display_messages.append({
                "role": "user",
                "content": content,
            })
            pending_activity = []

        elif role == "observation":
            observation = content.removeprefix(
                "Observation: "
            ).strip()

            pending_activity.append({
                "type": "observation",
                "content": observation,
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
                    "activity": pending_activity,
                })
                pending_activity = []

            else:
                # Do not expose the model's raw Thought text.
                pending_activity.append({
                    "type": "planning",
                    "content": "The agent is deciding how to proceed.",
                })
                pending_activity.append({
                    "type": "action",
                    "tool_name": parsed.tool_name or "Unknown tool",
                    "tool_input": str(parsed.tool_input or ""),
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


def load_session_or_raise(session_id: str) -> dict[str, Any]:
    """Load a session, translating storage errors into HTTP errors."""
    try:
        return session_manager.load_session(session_id)
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


def created_sort_key(session: dict[str, Any]) -> datetime:
    """Sort key for 'newest created first'. Unparseable dates go last."""
    try:
        return datetime.fromisoformat(session["created_at"]).astimezone()
    except (KeyError, TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def name_session_from_first_message(
    session_id: str,
    content: str,
) -> None:
    """Fallback name (the start of the first message) for a new session."""
    proposed_name = " ".join(content.split())[:40]
    proposed_name = proposed_name.replace("/", "-").replace("\\", "-")

    if not proposed_name:
        return

    try:
        session_manager.rename_session(session_id, proposed_name)
    except ValueError:
        # A duplicate display name must not prevent the response.
        pass


def apply_generated_title(
    llm: LLMClient,
    session_id: str,
    first_message: str,
) -> str | None:
    """Name a session with an LLM-written title. Returns it, or None."""
    try:
        title = generate_session_title(llm, first_message)
        title = make_title_unique(session_manager, title, session_id)
        renamed = session_manager.rename_session(session_id, title)
        return renamed["session_name"]
    except Exception as error:
        print(f"Could not generate a session title: {error}")
        return None


def keep_interrupted_answer(agent: ReActAgent, partial: str) -> None:
    """Save the part of an answer that was streamed before a stop.

    Without this, a stopped answer would vanish when the conversation is
    reloaded, because the agent only records a reply once it is complete.
    """
    text = partial.strip()

    if not text:
        return

    if agent.messages and agent.messages[-1].role == "assistant":
        return

    agent.messages.append(Message("assistant", f"Final Answer: {text}"))


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sessions")
def list_sessions() -> list[dict[str, Any]]:
    # Newest created first.
    sessions = sorted(
        session_manager.list_sessions(),
        key=created_sort_key,
        reverse=True,
    )

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
    session = load_session_or_raise(session_id)

    return serialize_session(session, include_messages=True)


@app.patch("/api/sessions/{session_id}")
def rename_session(
    session_id: str,
    request: RenameSessionRequest,
) -> dict[str, Any]:
    session = load_session_or_raise(session_id)
    lock = get_session_lock(session["session_id"])

    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail=BUSY_MESSAGE)

    try:
        renamed = session_manager.rename_session(
            session["session_id"],
            request.name,
        )
    except ValueError as error:
        status_code = 409 if "already exists" in str(error) else 422
        raise HTTPException(
            status_code=status_code,
            detail=str(error),
        ) from error
    finally:
        lock.release()

    return serialize_session(renamed)


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str) -> Response:
    session = load_session_or_raise(session_id)
    lock = get_session_lock(session["session_id"])

    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail=BUSY_MESSAGE)

    try:
        session_manager.remove_session(session["session_id"])
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        ) from error
    finally:
        lock.release()

    return Response(status_code=204)


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

    session = load_session_or_raise(session_id)
    resolved_id = session["session_id"]

    with get_session_lock(resolved_id):
        # Reload under the lock so an earlier run's save is included.
        session = load_session_or_raise(resolved_id)

        try:
            agent = build_agent(session)
            answer = agent.run(content)

            # Persist the full internal transcript, not just visible messages.
            session_manager.save_session(
                resolved_id,
                agent.get_messages(),
            )

            if not session["messages"]:
                title = apply_generated_title(
                    agent.llm,
                    resolved_id,
                    content,
                )

                if title is None:
                    name_session_from_first_message(resolved_id, content)

            updated_session = session_manager.load_session(resolved_id)

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


def sse(event: dict[str, Any]) -> str:
    """Format one Server-Sent Event."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def stream_agent_events(
    session_id: str,
    content: str,
) -> Iterator[str]:
    """Run the agent for one session, holding that session's lock."""
    with get_session_lock(session_id):
        yield from _stream_locked(session_id, content)


def _stream_locked(
    session_id: str,
    content: str,
) -> Iterator[str]:
    """Run the agent and yield its steps as Server-Sent Events.

    Event types: token, action, observation, final, error, title, and a
    last "done" event carrying the saved session and the full transcript.
    If the client disconnects (the user pressed stop), the generator is
    closed, the finally block saves what happened so far, and the
    "title" and "done" events are never produced.
    """
    try:
        # Loaded here, under the lock, so a previous (possibly stopped)
        # run has finished saving before this one starts.
        session = session_manager.load_session(session_id)
    except Exception as error:
        print(f"Could not load session: {error}")
        yield sse({
            "type": "error",
            "message": "The conversation could not be loaded.",
        })
        return

    is_first_message = not session["messages"]
    agent: ReActAgent | None = None
    answer = ""
    partial = ""
    completed = False
    succeeded = False

    try:
        agent = build_agent(session)

        for event in agent.run_stream(content):
            kind = event["type"]

            if kind == "token":
                partial += event["delta"]
            elif kind == "action":
                # Text before a tool call was not the answer.
                partial = ""
            elif kind == "final":
                answer = event["content"]
                completed = True
                succeeded = True
            elif kind == "error":
                answer = event["message"]
                completed = True

            yield sse(event)

    except Exception as error:
        print(f"Agent request failed: {error}")
        yield sse({
            "type": "error",
            "message": "The agent failed to process this message.",
        })

    finally:
        # Runs on success, on failure, and when the client disconnects
        # (the generator is closed). Nothing may be yielded in here.
        if agent is not None:
            try:
                if not completed:
                    keep_interrupted_answer(agent, partial)

                session_manager.save_session(
                    session_id,
                    agent.get_messages(),
                )

                if is_first_message:
                    # Fallback name; replaced by a generated title below
                    # when the run completes.
                    name_session_from_first_message(session_id, content)
            except Exception as error:
                print(f"Could not save session: {error}")

    if agent is None:
        return

    if is_first_message and succeeded:
        title = apply_generated_title(agent.llm, session_id, content)

        if title:
            yield sse({"type": "title", "name": title})

    try:
        updated_session = session_manager.load_session(session_id)
    except Exception as error:
        print(f"Could not reload session: {error}")
        yield sse({
            "type": "error",
            "message": "The conversation could not be saved.",
        })
        return

    yield sse({
        "type": "done",
        "session": serialize_session(updated_session),
        "messages": get_display_messages(agent.get_messages()),
        "answer": answer,
    })


@app.post("/api/sessions/{session_id}/messages/stream")
def stream_message(
    session_id: str,
    request: SendMessageRequest,
) -> StreamingResponse:
    content = request.content.strip()

    if not content:
        raise HTTPException(
            status_code=422,
            detail="Message content cannot be empty.",
        )

    # Validate before streaming starts, so a bad session id is a normal
    # 404/400 response rather than an error inside the event stream.
    session = load_session_or_raise(session_id)

    return StreamingResponse(
        stream_agent_events(session["session_id"], content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
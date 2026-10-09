import { useState, useRef, useEffect } from "react";
import { Bot, Sparkles } from "lucide-react";
import Sidebar from "./components/Sidebar";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000/api";

function formatMessages(messages = []) {
  return messages.map((message, index) => ({
    id: `${message.role}-${index}`,
    role: message.role,
    content: message.content,
  }));
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || `Request failed with status ${response.status}.`,
    );
  }

  return data;
}

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [collapsed, setCollapsed] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const [error, setError] = useState("");

  const messagesEndRef = useRef(null);

  const activeSession = sessions.find(
    (session) => session.id === activeSessionId,
  );

  const messages = activeSession?.messages ?? [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  useEffect(() => {
    let cancelled = false;

    async function loadSessions() {
      setIsLoadingSessions(true);

      try {
        await apiRequest("/health");

        const savedSessions = await apiRequest("/sessions");

        if (cancelled) {
          return;
        }

        setConnectionStatus("connected");
        setSessions(
          savedSessions.map((session) => ({
            ...session,
            messages: [],
          })),
        );

        // Open the most recently updated conversation, if one exists.
        const mostRecentSession = [...savedSessions].sort(
          (first, second) =>
            new Date(second.updated_at).getTime() -
            new Date(first.updated_at).getTime(),
        )[0];

        if (mostRecentSession) {
          await loadSession(mostRecentSession.id, cancelled);
        }
      } catch (requestError) {
        if (!cancelled) {
          setConnectionStatus("disconnected");
          setError(
            `Could not connect to the backend. ${requestError.message}`,
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoadingSessions(false);
        }
      }
    }

    async function loadSession(sessionId, cancelled) {
      const session = await apiRequest(`/sessions/${sessionId}`);

      if (cancelled) {
        return;
      }

      setSessions((currentSessions) =>
        currentSessions.map((item) =>
          item.id === session.id
            ? {
                ...item,
                name: session.name,
                messages: formatMessages(session.messages),
              }
            : item,
        ),
      );

      setActiveSessionId(session.id);
    }

    loadSessions();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleNewChat() {
    setError("");

    try {
      const session = await apiRequest("/sessions", {
        method: "POST",
        body: JSON.stringify({}),
      });

      const newSession = {
        ...session,
        messages: formatMessages(session.messages),
      };

      setSessions((currentSessions) => [
        newSession,
        ...currentSessions.filter((item) => item.id !== newSession.id),
      ]);

      setActiveSessionId(newSession.id);
    } catch (requestError) {
      setError(`Could not create a conversation. ${requestError.message}`);
    }
  }

  async function handleSelectSession(sessionId) {
    setError("");
    setActiveSessionId(sessionId);

    try {
      const session = await apiRequest(`/sessions/${sessionId}`);

      setSessions((currentSessions) =>
        currentSessions.map((item) =>
          item.id === session.id
            ? {
                ...item,
                name: session.name,
                messages: formatMessages(session.messages),
              }
            : item,
        ),
      );
    } catch (requestError) {
      setError(`Could not load this conversation. ${requestError.message}`);
    }
  }

  async function handleSendMessage(content) {
    const trimmedContent = content.trim();

    if (!activeSessionId || isThinking || !trimmedContent) {
      return;
    }

    const currentSessionId = activeSessionId;

    const userMessage = {
      id: `pending-${Date.now()}`,
      role: "user",
      content: trimmedContent,
    };

    setError("");
    setIsThinking(true);

    setSessions((currentSessions) =>
      currentSessions.map((session) =>
        session.id === currentSessionId
          ? {
              ...session,
              messages: [...session.messages, userMessage],
            }
          : session,
      ),
    );

    try {
      const result = await apiRequest(
        `/sessions/${currentSessionId}/messages`,
        {
          method: "POST",
          body: JSON.stringify({ content: trimmedContent }),
        },
      );

      setSessions((currentSessions) =>
        currentSessions.map((session) =>
          session.id === currentSessionId
            ? {
                ...session,
                name: result.session.name,
                messages: formatMessages(result.messages),
                updated_at: result.session.updated_at,
              }
            : session,
        ),
      );

      setConnectionStatus("connected");
    } catch (requestError) {
      setError(`The agent could not respond. ${requestError.message}`);
    } finally {
      setIsThinking(false);
    }
  }

  return (
    <div className="app-layout">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((current) => !current)}
        isLoadingSessions={isLoadingSessions}
      />

      <main className="chat-main">
        <header className="chat-header">
          <div className="chat-header__title">
            <Bot size={19} />
            <span>ReAct Agent</span>
          </div>

          <span className="connection-status">
            <span
              className={`connection-status__dot ${
                connectionStatus === "connected"
                  ? ""
                  : "connection-status__dot--disconnected"
              }`}
            />
            {connectionStatus === "connected"
              ? "Connected"
              : connectionStatus === "connecting"
                ? "Connecting..."
                : "Backend offline"}
          </span>
        </header>

        {error && (
          <div className="api-error" role="alert">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => setError("")}
              aria-label="Dismiss error"
            >
              Dismiss
            </button>
          </div>
        )}

        <section className="chat-content">
          {isLoadingSessions ? (
            <div className="chat-welcome">
              <div className="chat-welcome__icon">
                <Bot size={26} />
              </div>
              <h1>Loading your conversations...</h1>
              <p>Connecting to your local ReAct agent.</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="chat-welcome">
              <div className="chat-welcome__icon">
                <Sparkles size={26} />
              </div>

              <h1>
                {activeSession
                  ? activeSession.name
                  : "Where should we start?"}
              </h1>

              <p>
                Your personal AI agent, ready to reason, use tools, and find
                answers.
              </p>
            </div>
          ) : (
            <div className="chat-messages">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}

              {isThinking && (
                <div className="thinking-indicator">
                  <div className="thinking-indicator__icon">
                    <Bot size={18} />
                  </div>

                  <div>
                    <span className="thinking-indicator__label">
                      ReAct Agent is thinking
                    </span>
                    <div className="thinking-indicator__dots">
                      <span />
                      <span />
                      <span />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </section>

        <footer className="chat-footer">
          <ChatInput
            onSend={handleSendMessage}
            disabled={
              !activeSessionId ||
              isThinking ||
              isLoadingSessions ||
              connectionStatus !== "connected"
            }
          />
        </footer>
      </main>
    </div>
  );
}
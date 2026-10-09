import { useState, useRef, useEffect } from "react";
import { Bot, Sparkles } from "lucide-react";
import Sidebar from "./components/Sidebar";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import "./App.css";

const initialSessions = [
  {
    id: "session-1",
    name: "Understanding ReAct agents",
    messages: [
      {
        id: "message-1",
        role: "user",
        content: "What is a ReAct agent?",
      },
      {
        id: "message-2",
        role: "assistant",
        content:
          "A ReAct agent combines reasoning and acting. It can decide which tool to use, observe the result, and use that result to continue solving a problem.",
      },
    ],
  },
  {
    id: "session-2",
    name: "Python tool implementation",
    messages: [],
  },
  {
    id: "session-3",
    name: "How context management works",
    messages: [],
  },
];

export default function App() {
  const [sessions, setSessions] = useState(initialSessions);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [collapsed, setCollapsed] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef(null);

  const activeSession = sessions.find(
    (session) => session.id === activeSessionId,
  );

  const messages = activeSession?.messages ?? [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  function handleNewChat() {
    const newSession = {
      id: `session-${Date.now()}`,
      name: "New chat",
      messages: [],
    };

    setSessions((currentSessions) => [newSession, ...currentSessions]);
    setActiveSessionId(newSession.id);
  }

  function handleSelectSession(sessionId) {
    setActiveSessionId(sessionId);
  }

  async function handleSendMessage(content) {
    if (!activeSessionId || isThinking || !content.trim()) {
      return;
    }

    const userMessage = {
      id: `message-${Date.now()}`,
      role: "user",
      content: content.trim(),
    };

    const currentSessionId = activeSessionId;

    setSessions((currentSessions) =>
      currentSessions.map((session) =>
        session.id === currentSessionId
          ? {
              ...session,
              name:
                session.messages.length === 0
                  ? content.trim().slice(0, 35)
                  : session.name,
              messages: [...session.messages, userMessage],
            }
          : session,
      ),
    );

    setIsThinking(true);

    try {
      // Temporary mock response. We will replace this with a backend request.
      await new Promise((resolve) => setTimeout(resolve, 900));

      const assistantMessage = {
        id: `message-${Date.now()}`,
        role: "assistant",
        content: `I received your message:\n\n"${content.trim()}"\n\nThis is a placeholder response. In the next stage, we'll connect this chat to your Python ReAct agent.`,
      };

      setSessions((currentSessions) =>
        currentSessions.map((session) =>
          session.id === currentSessionId
            ? {
                ...session,
                messages: [...session.messages, assistantMessage],
              }
            : session,
        ),
      );
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
      />

      <main className="chat-main">
        <header className="chat-header">
          <div className="chat-header__title">
            <Bot size={19} />
            <span>ReAct Agent</span>
          </div>

          <span className="connection-status">
            <span className="connection-status__dot" />
            Mock mode
          </span>
        </header>

        <section className="chat-content">
          {messages.length === 0 ? (
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
            disabled={!activeSessionId || isThinking}
          />
        </footer>
      </main>
    </div>
  );
}
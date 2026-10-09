import { useState } from "react";
import { Bot, Sparkles } from "lucide-react";
import Sidebar from "./components/Sidebar";
import "./App.css";

const initialSessions = [
{ id: "session-1", name: "Understanding ReAct agents" },
{ id: "session-2", name: "Python tool implementation" },
{ id: "session-3", name: "How context management works" },
];

export default function App() {
const [sessions, setSessions] = useState(initialSessions);
const [activeSessionId, setActiveSessionId] = useState(null);
const [collapsed, setCollapsed] = useState(false);

function handleNewChat() {
const newSession = {
id: `session-${Date.now()}`,
name: "New chat",
};

```
setSessions((currentSessions) => [newSession, ...currentSessions]);
setActiveSessionId(newSession.id);
```

}

function handleSelectSession(sessionId) {
setActiveSessionId(sessionId);
}

const activeSession = sessions.find(
(session) => session.id === activeSessionId,
);

return ( <div className="app-layout">
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
        Local interface
      </span>
    </header>

    <section className="chat-welcome">
      <div className="chat-welcome__icon">
        <Sparkles size={26} />
      </div>

      <h1>
        {activeSession ? activeSession.name : "Where should we start?"}
      </h1>

      <p>
        Your personal AI agent, ready to reason, use tools, and find answers.
      </p>

      <div className="chat-suggestions">
        <button onClick={handleNewChat}>
          <span>＋</span>
          Start a new conversation
        </button>
        <button onClick={() => setCollapsed((current) => !current)}>
          <span>☰</span>
          Customize your workspace
        </button>
      </div>
    </section>

    <footer className="chat-footer">
      <p>The chat interface is under construction.</p>
    </footer>
  </main>
</div>

);
}

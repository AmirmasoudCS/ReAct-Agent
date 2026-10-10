import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatHeader from "./components/ChatHeader";
import ChatWelcome from "./components/ChatWelcome";
import MessageList from "./components/MessageList";
import ChatInput from "./components/ChatInput";
import { API_BASE_URL, APP_NAME } from "./config";
import { createHttpClient } from "./api/httpClient";
import { createAgentApi } from "./api/agentApi";
import { useSessions } from "./hooks/useSessions";
import { useChat } from "./hooks/useChat";
import "./App.css";
import { usePersistentState } from "./hooks/usePersistentState";

// Created once, outside the component, so hooks get a stable reference.
const api = createAgentApi(createHttpClient(API_BASE_URL));

export default function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [showActivity, setShowActivity] = usePersistentState("showActivity", true);

  const {
    sessions,
    activeSession,
    activeSessionId,
    isLoading,
    connectionStatus,
    error,
    clearError,
    reportError,
    patchSession,
    createSession,
    selectSession,
    reload,
  } = useSessions(api);

  const { sendMessage, isThinking } = useChat({
    api,
    sessionId: activeSessionId,
    patchSession,
    onError: reportError,
  });

  const messages = activeSession?.messages ?? [];

  return (
    <div className="app-layout">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={() => createSession()}
        onSelectSession={selectSession}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((current) => !current)}
        isLoadingSessions={isLoading}
      />

      <main className="chat-main">
        <ChatHeader
          title={APP_NAME}
          connectionStatus={connectionStatus}
          showActivity={showActivity}
          onToggleActivity={() => setShowActivity((current) => !current)}
          onRetry={reload}
        />

        {error && (
          <div className="api-error" role="alert">
            <span>{error}</span>
            <button type="button" onClick={clearError}>
              Dismiss
            </button>
          </div>
        )}

        <section className="chat-content">
          {isLoading ? (
            <ChatWelcome loading />
          ) : messages.length === 0 ? (
            <ChatWelcome title={activeSession?.name ?? "Where should we start?"} />
          ) : (
            <MessageList
              messages={messages}
              isThinking={isThinking}
              showActivity={showActivity}
              agentName={APP_NAME}
            />
          )}
        </section>

        <footer className="chat-footer">
          <ChatInput
            onSend={sendMessage}
            disabled={
              !activeSessionId ||
              isThinking ||
              isLoading ||
              connectionStatus !== "connected"
            }
          />
        </footer>
      </main>
    </div>
  );
}
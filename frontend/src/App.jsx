import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatHeader from "./components/ChatHeader";
import ChatWelcome from "./components/ChatWelcome";
import MessageList from "./components/MessageList";
import ChatInput from "./components/ChatInput";
import SettingsModal from "./components/SettingsModal";
import HelpModal from "./components/HelpModal";
import ArxivResults from "./components/ArxivResults";
import DocumentResults from "./components/DocumentResults";
import { API_BASE_URL, APP_NAME } from "./config";
import { createHttpClient } from "./api/httpClient";
import { createAgentApi } from "./api/agentApi";
import { useSessions } from "./hooks/useSessions";
import { useChat } from "./hooks/useChat";
import { useDocuments } from "./hooks/useDocuments";
import "./App.css";
import { usePersistentState } from "./hooks/usePersistentState";

// Created once, outside the component, so hooks get a stable reference.
const api = createAgentApi(createHttpClient(API_BASE_URL));

// Custom result views, keyed by lowercase tool name.
const toolRenderers = {
  arxiv_search: (step) => <ArxivResults text={step.result} />,
  document_search: (step) => <DocumentResults text={step.result} />,
};

export default function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
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
    renameSession,
    deleteSession,
    reload,
  } = useSessions(api);

  const { sendMessage, stopMessage, isThinking } = useChat({
    api,
    sessionId: activeSessionId,
    patchSession,
    onError: reportError,
  });

  const {
    documents,
    isUploading,
    upload: uploadDocuments,
    remove: removeDocument,
  } = useDocuments({
    api,
    sessionId: activeSessionId,
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
        onRenameSession={renameSession}
        onDeleteSession={deleteSession}
        onOpenSettings={() => setSettingsOpen(true)}
        onOpenHelp={() => setHelpOpen(true)}
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
              toolRenderers={toolRenderers}
            />
          )}
        </section>

        <footer className="chat-footer">
          <ChatInput
            onSend={sendMessage}
            onStop={stopMessage}
            isBusy={isThinking}
            disabled={
              !activeSessionId ||
              isLoading ||
              connectionStatus !== "connected"
            }
            documents={documents}
            isUploading={isUploading}
            onUpload={uploadDocuments}
            onRemoveDocument={removeDocument}
          />
        </footer>
      </main>

      {settingsOpen && (
        <SettingsModal api={api} onClose={() => setSettingsOpen(false)} />
      )}

      {helpOpen && <HelpModal onClose={() => setHelpOpen(false)} />}
    </div>
  );
}
import { useEffect, useRef } from "react";
import { Bot } from "lucide-react";
import ChatMessage from "./ChatMessage";
import ActivityPanel from "./ActivityPanel";
import "./MessageList.css";

export default function MessageList({
  messages,
  isThinking = false,
  showActivity = false,
  agentName = "ReAct Agent",
  toolRenderers,
}) {
  const endRef = useRef(null);

  const lastMessage = messages[messages.length - 1];
  const isStreaming = Boolean(lastMessage?.streaming);

  // Show the "thinking" dots until answer text is actually flowing.
  // This also covers the pauses between a tool result and the next step.
  const showThinking =
    isThinking && !(isStreaming && Boolean(lastMessage?.content));

  useEffect(() => {
    // Smooth scrolling restarts on every token and lags behind the text,
    // so follow the stream instantly and animate only for new messages.
    endRef.current?.scrollIntoView({
      behavior: isStreaming ? "auto" : "smooth",
    });
  }, [messages, isThinking, showActivity, isStreaming]);

  return (
    <div className="chat-messages">
      {messages.map((message) => (
        <div className="chat-message-group" key={message.id}>
          <ChatMessage message={message} agentName={agentName} />

          {showActivity && message.role === "assistant" && (
            <ActivityPanel
              activity={message.activity}
              toolRenderers={toolRenderers}
              live={Boolean(message.streaming)}
            />
          )}
        </div>
      ))}

      {showThinking && (
        <div className="thinking-indicator">
          <div className="thinking-indicator__icon">
            <Bot size={18} />
          </div>

          <div>
            <span className="thinking-indicator__label">
              {agentName} is thinking
            </span>
            <div className="thinking-indicator__dots">
              <span />
              <span />
              <span />
            </div>
          </div>
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}
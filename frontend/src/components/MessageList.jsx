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

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking, showActivity]);

  return (
    <div className="chat-messages">
      {messages.map((message) => (
        <div className="chat-message-group" key={message.id}>
          <ChatMessage message={message} agentName={agentName} />

          {showActivity && message.role === "assistant" && (
            <ActivityPanel
              activity={message.activity}
              toolRenderers={toolRenderers}
            />
          )}
        </div>
      ))}

      {isThinking && (
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
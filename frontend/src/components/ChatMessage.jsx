import { Bot, User } from "lucide-react";
import MarkdownContent from "./MarkdownContent";
import CopyButton from "./CopyButton";
import "./ChatMessage.css";

export default function ChatMessage({ message, agentName = "ReAct Agent" }) {
  const isUser = message.role === "user";
  const hasText = Boolean(message.content);

  return (
    <article
      className={`chat-message ${
        isUser ? "chat-message--user" : "chat-message--assistant"
      }`}
    >
      <div className="chat-message__avatar">
        {isUser ? <User size={17} /> : <Bot size={18} />}
      </div>

      <div className="chat-message__content">
        <span className="chat-message__role">{isUser ? "You" : agentName}</span>

        {isUser ? (
          <div className="chat-message__text chat-message__text--plain">
            {message.content}
          </div>
        ) : (
          (hasText || message.streaming) && (
            <div
              className={`chat-message__text ${
                message.streaming ? "chat-message__text--streaming" : ""
              }`}
            >
              {hasText && <MarkdownContent>{message.content}</MarkdownContent>}
              {message.streaming && (
                <span className="chat-message__cursor" aria-hidden="true" />
              )}
            </div>
          )
        )}

        {!isUser && hasText && !message.streaming && (
          <div className="chat-message__actions">
            <CopyButton text={message.content} label="Copy answer" />
          </div>
        )}

        {message.status === "failed" && (
          <span className="chat-message__error" role="status">
            Not sent. Check the connection and try again.
          </span>
        )}

        {message.interrupted && (
          <span className="chat-message__error" role="status">
            The response was interrupted.
          </span>
        )}

        {message.stopped && (
          <span className="chat-message__note" role="status">
            Stopped.
          </span>
        )}
      </div>
    </article>
  );
}
import { Bot, User } from "lucide-react";
import MarkdownContent from "./MarkdownContent";
import CopyButton from "./CopyButton";
import "./ChatMessage.css";

export default function ChatMessage({ message, agentName = "ReAct Agent" }) {
  const isUser = message.role === "user";

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
          <div className="chat-message__text">
            <MarkdownContent>{message.content}</MarkdownContent>
          </div>
        )}

        {!isUser && (
          <div className="chat-message__actions">
            <CopyButton text={message.content} label="Copy answer" />
          </div>
        )}

        {message.status === "failed" && (
          <span className="chat-message__error" role="status">
            Not sent. Check the connection and try again.
          </span>
        )}
      </div>
    </article>
  );
}
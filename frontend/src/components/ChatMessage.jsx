import { Bot, User } from "lucide-react";
import "./ChatMessage.css";

export default function ChatMessage({ message }) {
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
        <span className="chat-message__role">
          {isUser ? "You" : "ReAct Agent"}
        </span>

        <div className="chat-message__text">{message.content}</div>
      </div>
    </article>
  );
}
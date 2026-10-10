import { Bot, Sparkles } from "lucide-react";

export default function ChatWelcome({
  loading = false,
  title,
  subtitle = "Your personal AI agent, ready to reason, use tools, and find answers.",
}) {
  return (
    <div className="chat-welcome">
      <div className="chat-welcome__icon">
        {loading ? <Bot size={26} /> : <Sparkles size={26} />}
      </div>

      <h1>{loading ? "Loading your conversations..." : title}</h1>
      <p>{loading ? "Connecting to your local ReAct agent." : subtitle}</p>
    </div>
  );
}
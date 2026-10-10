import { Bot, Eye, EyeOff } from "lucide-react";

const STATUS_LABELS = {
  connected: "Connected",
  connecting: "Connecting...",
  disconnected: "Backend offline",
};

export default function ChatHeader({
  title,
  connectionStatus,
  showActivity,
  onToggleActivity,
  onRetry,
}) {
  return (
    <header className="chat-header">
      <div className="chat-header__title">
        <Bot size={19} />
        <span>{title}</span>
      </div>

      <div className="chat-header__actions">
        <button
          type="button"
          className={`activity-toggle ${
            showActivity ? "activity-toggle--active" : ""
          }`}
          onClick={onToggleActivity}
          aria-pressed={showActivity}
          title={showActivity ? "Hide agent activity" : "Show agent activity"}
        >
          {showActivity ? <EyeOff size={16} /> : <Eye size={16} />}
          <span>Activity</span>
        </button>

        {connectionStatus === "disconnected" && onRetry && (
          <button type="button" className="activity-toggle" onClick={onRetry}>
            <span>Retry</span>
          </button>
        )}

        <span className="connection-status">
          <span
            className={`connection-status__dot ${
              connectionStatus === "connected"
                ? ""
                : "connection-status__dot--disconnected"
            }`}
          />
          {STATUS_LABELS[connectionStatus]}
        </span>
      </div>
    </header>
  );
}
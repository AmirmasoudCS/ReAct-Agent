import { useState } from "react";
import {
Bot,
CircleHelp,
MessageSquare,
PanelLeftClose,
PanelLeftOpen,
Plus,
Search,
Settings,
} from "lucide-react";
import "./Sidebar.css";

export default function Sidebar({
sessions,
activeSessionId,
onNewChat,
onSelectSession,
collapsed,
onToggleCollapse,
}) {
const [searchQuery, setSearchQuery] = useState("");

const filteredSessions = sessions.filter((session) =>
session.name.toLowerCase().includes(searchQuery.toLowerCase()),
);

return (
<aside className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}> <div className="sidebar__top"> <div className="sidebar__brand"> <div className="sidebar__logo"> <Bot size={22} /> </div>

      {!collapsed && <span>ReAct Agent</span>}
    </div>

    <button
      className="icon-button sidebar__collapse"
      onClick={onToggleCollapse}
      title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
    >
      {collapsed ? (
        <PanelLeftOpen size={19} />
      ) : (
        <PanelLeftClose size={19} />
      )}
    </button>
  </div>

  <div className="sidebar__actions">
    <button
      className="sidebar__action sidebar__action--primary"
      onClick={onNewChat}
      title="New chat"
    >
      <Plus size={19} />
      {!collapsed && <span>New chat</span>}
    </button>

    {!collapsed && (
      <label className="sidebar__search">
        <Search size={17} />
        <input
          type="search"
          placeholder="Search chats"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
        />
      </label>
    )}
  </div>

  <div className="sidebar__history">
    {!collapsed && (
      <p className="sidebar__section-label">Your conversations</p>
    )}

    {filteredSessions.map((session) => (
      <button
        key={session.id}
        className={`sidebar__session ${
          activeSessionId === session.id
            ? "sidebar__session--active"
            : ""
        }`}
        onClick={() => onSelectSession(session.id)}
        title={session.name}
      >
        <MessageSquare size={17} />
        {!collapsed && <span>{session.name}</span>}
      </button>
    ))}

    {!collapsed && filteredSessions.length === 0 && (
      <p className="sidebar__empty">
        {sessions.length === 0
          ? "Your conversations will appear here."
          : "No matching conversations."}
      </p>
    )}
  </div>

  <div className="sidebar__bottom">
    <button
      className="sidebar__session"
      title="Settings"
      onClick={() => alert("Settings will be implemented later.")}
    >
      <Settings size={18} />
      {!collapsed && <span>Settings</span>}
    </button>

    <button
      className="sidebar__session"
      title="Help"
      onClick={() => alert("Help will be implemented later.")}
    >
      <CircleHelp size={18} />
      {!collapsed && <span>Help</span>}
    </button>

    <div className="sidebar__profile">
      <div className="sidebar__avatar">R</div>
      {!collapsed && (
        <div className="sidebar__profile-info">
          <span className="sidebar__profile-name">ReAct Agent</span>
          <span className="sidebar__profile-subtitle">
            Local AI assistant
          </span>
        </div>
      )}
    </div>
  </div>
</aside>

);
}

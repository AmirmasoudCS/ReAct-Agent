import { useEffect, useRef, useState } from "react";
import {
  Bot,
  CircleHelp,
  MessageSquare,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  Search,
  Settings,
  Trash2,
} from "lucide-react";
import "./Sidebar.css";

export default function Sidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  collapsed,
  onToggleCollapse,
  isLoadingSessions = false,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [menuId, setMenuId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState("");

  // Enter and blur both try to save; this makes sure only one of them does.
  const finishedRef = useRef(false);

  const filteredSessions = sessions.filter((session) =>
    session.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  // Close the open "..." menu on an outside click or Escape.
  useEffect(() => {
    if (menuId === null) {
      return undefined;
    }

    function handlePointerDown(event) {
      if (!event.target.closest(".sidebar__menu, .sidebar__more")) {
        setMenuId(null);
      }
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setMenuId(null);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuId]);

  function startRename(session) {
    setMenuId(null);
    setDraft(session.name);
    finishedRef.current = false;
    setEditingId(session.id);
  }

  function cancelRename() {
    finishedRef.current = true;
    setEditingId(null);
  }

  async function commitRename(session) {
    if (finishedRef.current) {
      return;
    }

    const name = draft.trim();

    if (!name || name === session.name) {
      cancelRename();
      return;
    }

    finishedRef.current = true;

    const saved = await onRenameSession(session.id, name);

    if (saved) {
      setEditingId(null);
    } else {
      // Keep the field open so the name can be corrected. The reason
      // (for example "already exists") is shown in the error banner.
      finishedRef.current = false;
    }
  }

  function handleDelete(session) {
    setMenuId(null);

    const confirmed = window.confirm(
      `Delete "${session.name}"? This cannot be undone.`,
    );

    if (confirmed) {
      onDeleteSession(session.id);
    }
  }

  return (
    <aside className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}>
      <div className="sidebar__top">
        <div className="sidebar__brand">
          <div className="sidebar__logo">
            <Bot size={22} />
          </div>

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
          disabled={isLoadingSessions}
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

        {filteredSessions.map((session) => {
          const isActive = activeSessionId === session.id;
          const isEditing = editingId === session.id;
          const isMenuOpen = menuId === session.id;

          return (
            <div
              key={session.id}
              className={`sidebar__row ${
                isActive ? "sidebar__row--active" : ""
              }`}
            >
              {isEditing && !collapsed ? (
                <div className="sidebar__session sidebar__session--editing">
                  <MessageSquare size={17} />
                  <input
                    className="sidebar__rename-input"
                    value={draft}
                    maxLength={80}
                    autoFocus
                    aria-label="Conversation name"
                    onFocus={(event) => event.target.select()}
                    onChange={(event) => setDraft(event.target.value)}
                    onBlur={() => commitRename(session)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        commitRename(session);
                      } else if (event.key === "Escape") {
                        event.preventDefault();
                        cancelRename();
                      }
                    }}
                  />
                </div>
              ) : (
                <>
                  <button
                    className={`sidebar__session ${
                      isActive ? "sidebar__session--active" : ""
                    }`}
                    onClick={() => onSelectSession(session.id)}
                    title={session.name}
                  >
                    <MessageSquare size={17} />
                    {!collapsed && <span>{session.name}</span>}
                  </button>

                  {!collapsed && (
                    <button
                      type="button"
                      className={`sidebar__more ${
                        isMenuOpen ? "sidebar__more--open" : ""
                      }`}
                      onClick={() =>
                        setMenuId(isMenuOpen ? null : session.id)
                      }
                      aria-label={`Options for ${session.name}`}
                      aria-haspopup="menu"
                      aria-expanded={isMenuOpen}
                    >
                      <MoreHorizontal size={17} />
                    </button>
                  )}

                  {isMenuOpen && (
                    <div className="sidebar__menu" role="menu">
                      <button
                        type="button"
                        role="menuitem"
                        className="sidebar__menu-item"
                        onClick={() => startRename(session)}
                      >
                        <Pencil size={15} />
                        <span>Rename</span>
                      </button>

                      <button
                        type="button"
                        role="menuitem"
                        className="sidebar__menu-item sidebar__menu-item--danger"
                        onClick={() => handleDelete(session)}
                      >
                        <Trash2 size={15} />
                        <span>Delete</span>
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}

        {!collapsed && filteredSessions.length === 0 && (
          <p className="sidebar__empty">
            {isLoadingSessions
              ? "Loading conversations..."
              : sessions.length === 0
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
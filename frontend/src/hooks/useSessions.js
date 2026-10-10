import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Owns the session list, the active session, and backend connectivity.
 * Receives the API object as an argument, so it works with any backend
 * that implements: health, listSessions, getSession, createSession,
 * renameSession, deleteSession.
 *
 * The backend returns sessions newest-created first; new sessions are
 * added at the top, so the list stays in that order.
 */
export function useSessions(api) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const [error, setError] = useState("");

  const loadToken = useRef(0);

  const patchSession = useCallback((id, updates) => {
    setSessions((current) =>
      current.map((session) =>
        session.id === id
          ? {
              ...session,
              ...(typeof updates === "function" ? updates(session) : updates),
            }
          : session,
      ),
    );
  }, []);

  const reportError = useCallback((prefix, requestError) => {
    setError(`${prefix} ${requestError.message}`);

    if (requestError.status === 0) {
      setConnectionStatus("disconnected");
    }
  }, []);

  const load = useCallback(async () => {
    const token = ++loadToken.current;
    const isStale = () => token !== loadToken.current;

    try {
      await api.health();
      const saved = await api.listSessions();

      if (isStale()) return;

      setConnectionStatus("connected");
      setSessions(saved.map((session) => ({ ...session, messages: [] })));

      // Resume the conversation used most recently.
      const latest = [...saved].sort(
        (a, b) => new Date(b.updated_at) - new Date(a.updated_at),
      )[0];

      if (latest) {
        const session = await api.getSession(latest.id);

        if (isStale()) return;

        setSessions((current) =>
          current.map((item) =>
            item.id === session.id
              ? { ...item, name: session.name, messages: session.messages }
              : item,
          ),
        );
        setActiveSessionId(session.id);
      }
    } catch (requestError) {
      if (!isStale()) {
        setConnectionStatus("disconnected");
        setError(`Could not connect to the backend. ${requestError.message}`);
      }
    } finally {
      if (!isStale()) {
        setIsLoading(false);
      }
    }
  }, [api]);

  useEffect(() => {
    load();

    return () => {
      loadToken.current += 1;
    };
  }, [load]);

  const reload = useCallback(() => {
    setIsLoading(true);
    setConnectionStatus("connecting");
    setError("");
    return load();
  }, [load]);

  const createSession = useCallback(
    async (name) => {
      setError("");

      try {
        const session = await api.createSession(name);

        setSessions((current) => [
          session,
          ...current.filter((item) => item.id !== session.id),
        ]);
        setActiveSessionId(session.id);
      } catch (requestError) {
        reportError("Could not create a conversation.", requestError);
      }
    },
    [api, reportError],
  );

  const selectSession = useCallback(
    async (id) => {
      setError("");
      setActiveSessionId(id);

      try {
        const session = await api.getSession(id);
        patchSession(id, { name: session.name, messages: session.messages });
      } catch (requestError) {
        reportError("Could not load this conversation.", requestError);
      }
    },
    [api, patchSession, reportError],
  );

  // Resolves to true on success. On failure the reason is shown through
  // `error` (for example "A session named 'X' already exists.").
  const renameSession = useCallback(
    async (id, name) => {
      const trimmed = name.trim();

      if (!trimmed) {
        return false;
      }

      setError("");

      try {
        const result = await api.renameSession(id, trimmed);

        patchSession(id, { name: result.name, updated_at: result.updated_at });
        return true;
      } catch (requestError) {
        reportError("Could not rename this conversation.", requestError);
        return false;
      }
    },
    [api, patchSession, reportError],
  );

  // Removes the session. If it was the open one, the next session in the
  // list (the newest remaining) is opened, or the chat is emptied.
  const deleteSession = useCallback(
    async (id) => {
      setError("");

      try {
        await api.deleteSession(id);
      } catch (requestError) {
        reportError("Could not delete this conversation.", requestError);
        return false;
      }

      const remaining = sessions.filter((session) => session.id !== id);

      setSessions(remaining);

      if (id === activeSessionId) {
        if (remaining.length > 0) {
          await selectSession(remaining[0].id);
        } else {
          setActiveSessionId(null);
        }
      }

      return true;
    },
    [api, sessions, activeSessionId, selectSession, reportError],
  );

  const activeSession =
    sessions.find((session) => session.id === activeSessionId) ?? null;

  return {
    sessions,
    activeSession,
    activeSessionId,
    isLoading,
    connectionStatus,
    error,
    clearError: () => setError(""),
    reportError,
    patchSession,
    createSession,
    selectSession,
    renameSession,
    deleteSession,
    reload,
  };
}
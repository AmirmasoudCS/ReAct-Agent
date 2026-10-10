import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Owns the session list, the active session, and backend connectivity.
 * Receives the API object as an argument, so it works with any backend
 * that implements: health, listSessions, getSession, createSession.
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
    reload,
  };
}
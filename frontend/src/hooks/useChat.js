import { useCallback, useState } from "react";

/**
 * Sending messages and tracking "the agent is thinking" per session.
 * Works with any api object that implements sendMessage(id, content).
 *
 * Returns the user's message immediately (optimistic), then replaces the
 * whole transcript with the server's version when the agent finishes.
 * If the request fails, the message stays visible and is marked "failed".
 */
export function useChat({ api, sessionId, patchSession, onError }) {
  const [thinkingIds, setThinkingIds] = useState([]);

  const isThinking = thinkingIds.includes(sessionId);

  const sendMessage = useCallback(
    async (content) => {
      const text = content.trim();

      if (!sessionId || !text || thinkingIds.includes(sessionId)) {
        return;
      }

      const targetId = sessionId;
      const pendingId = `pending-${Date.now()}`;

      patchSession(targetId, (session) => ({
        messages: [
          ...session.messages,
          { id: pendingId, role: "user", content: text, activity: [] },
        ],
      }));
      setThinkingIds((ids) => [...ids, targetId]);

      try {
        const result = await api.sendMessage(targetId, text);

        patchSession(targetId, {
          name: result.session.name,
          updated_at: result.session.updated_at,
          messages: result.messages,
        });
      } catch (requestError) {
        patchSession(targetId, (session) => ({
          messages: session.messages.map((message) =>
            message.id === pendingId ? { ...message, status: "failed" } : message,
          ),
        }));
        onError?.("The agent could not respond.", requestError);
      } finally {
        setThinkingIds((ids) => ids.filter((id) => id !== targetId));
      }
    },
    [api, sessionId, thinkingIds, patchSession, onError],
  );

  return { sendMessage, isThinking };
}
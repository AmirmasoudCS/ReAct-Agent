import { useCallback, useState } from "react";

/**
 * Sending messages and tracking "the agent is thinking" per session.
 * Works with any api object that implements
 * streamMessage(id, content, { onEvent, signal }).
 *
 * The user's message appears immediately (optimistic). The assistant
 * message is created on the first token or tool call, then grows live.
 * When the agent finishes, the whole transcript is replaced with the
 * server's version. If the request fails before anything arrives, the
 * user's message is marked "failed"; if it fails midway, the partial
 * answer is kept and marked "interrupted".
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
      const assistantId = `stream-${Date.now()}`;

      let created = false;
      let answerText = "";
      let activity = [];
      let streamError = null;
      let frame = null;

      // Create the assistant message on first use, update it afterwards.
      const upsert = (changes) => {
        const isNew = !created;
        created = true;

        patchSession(targetId, (session) =>
          isNew
            ? {
                messages: [
                  ...session.messages,
                  {
                    id: assistantId,
                    role: "assistant",
                    content: "",
                    activity: [],
                    streaming: true,
                    ...changes,
                  },
                ],
              }
            : {
                messages: session.messages.map((message) =>
                  message.id === assistantId
                    ? { ...message, ...changes }
                    : message,
                ),
              },
        );
      };

      const cancelFrame = () => {
        if (frame !== null) {
          cancelAnimationFrame(frame);
          frame = null;
        }
      };

      // Batch token updates to one render per animation frame.
      const scheduleTextFlush = () => {
        if (frame !== null) return;

        frame = requestAnimationFrame(() => {
          frame = null;
          upsert({ content: answerText });
        });
      };

      const handleEvent = (event) => {
        switch (event.type) {
          case "token":
            answerText += event.delta;
            scheduleTextFlush();
            break;

          case "action":
            activity = [
              ...activity,
              {
                type: "action",
                tool_name: event.tool_name,
                tool_input: event.tool_input,
              },
            ];
            upsert({ activity });
            break;

          case "observation":
            activity = [
              ...activity,
              { type: "observation", content: event.content },
            ];
            upsert({ activity });
            break;

          case "final":
            cancelFrame();
            // Plain replies are not streamed; they only arrive here.
            upsert({ content: answerText || event.content });
            break;

          case "error":
            cancelFrame();
            streamError = event.message;
            break;

          default:
            break;
        }
      };

      patchSession(targetId, (session) => ({
        messages: [
          ...session.messages,
          { id: pendingId, role: "user", content: text, activity: [] },
        ],
      }));
      setThinkingIds((ids) => [...ids, targetId]);

      try {
        const result = await api.streamMessage(targetId, text, {
          onEvent: handleEvent,
        });

        // The server transcript is the source of truth. Errors are not part
        // of it, so keep the error text visible as its own message.
        const messages = streamError
          ? [
              ...result.messages,
              {
                id: `error-${Date.now()}`,
                role: "assistant",
                content: streamError,
                activity: [],
                isError: true,
              },
            ]
          : result.messages;

        patchSession(targetId, {
          name: result.session.name,
          updated_at: result.session.updated_at,
          messages,
        });
      } catch (requestError) {
        cancelFrame();

        if (created) {
          // Partial answer received: keep it and flag it.
          upsert({ content: answerText, streaming: false, interrupted: true });
        } else {
          patchSession(targetId, (session) => ({
            messages: session.messages.map((message) =>
              message.id === pendingId
                ? { ...message, status: "failed" }
                : message,
            ),
          }));
        }

        onError?.("The agent could not respond.", requestError);
      } finally {
        cancelFrame();
        setThinkingIds((ids) => ids.filter((id) => id !== targetId));
      }
    },
    [api, sessionId, thinkingIds, patchSession, onError],
  );

  return { sendMessage, isThinking };
}
import { useCallback, useRef, useState } from "react";

/**
 * Sending messages and tracking "the agent is thinking" per session.
 * Works with any api object that implements
 * streamMessage(id, content, { onEvent, signal }).
 *
 * The user's message appears immediately (optimistic). The assistant
 * message is created on the first token or tool call, then grows live.
 * When the agent finishes, the whole transcript is replaced with the
 * server's version.
 *
 * stopMessage() aborts the running request for the active session; the
 * partial answer stays visible and is marked "stopped". If a request
 * fails before anything arrives, the user's message is marked "failed";
 * if it fails midway, the partial answer is kept and marked "interrupted".
 */
export function useChat({ api, sessionId, patchSession, onError }) {
  const [thinkingIds, setThinkingIds] = useState([]);
  const controllers = useRef(new Map());

  const isThinking = thinkingIds.includes(sessionId);

  const stopMessage = useCallback(() => {
    controllers.current.get(sessionId)?.abort();
  }, [sessionId]);

  const sendMessage = useCallback(
    async (content) => {
      const text = content.trim();

      if (!sessionId || !text || thinkingIds.includes(sessionId)) {
        return;
      }

      const targetId = sessionId;
      const pendingId = `pending-${Date.now()}`;
      const assistantId = `stream-${Date.now()}`;
      const controller = new AbortController();

      controllers.current.set(targetId, controller);

      let created = false;
      let finalReceived = false;
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
            // Anything streamed before a tool call was not the answer.
            answerText = "";
            activity = [
              ...activity,
              {
                type: "action",
                tool_name: event.tool_name,
                tool_input: event.tool_input,
              },
            ];
            cancelFrame();
            upsert({ content: "", activity });
            break;

          case "observation":
            activity = [
              ...activity,
              { type: "observation", content: event.content },
            ];
            upsert({ activity });
            break;

          case "final":
            finalReceived = true;
            cancelFrame();
            // Plain replies are not always streamed; they may only arrive here.
            upsert({ content: answerText || event.content });
            break;

          case "error":
            cancelFrame();
            streamError = event.message;
            break;

          case "title":
            patchSession(targetId, { name: event.name });
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
          signal: controller.signal,
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

        // The user pressed stop. Keep what has arrived, without an error.
        if (requestError.name === "AbortError") {
          if (created) {
            upsert({
              content: answerText,
              streaming: false,
              stopped: !finalReceived,
            });
          }
          return;
        }

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
        controllers.current.delete(targetId);
        setThinkingIds((ids) => ids.filter((id) => id !== targetId));
      }
    },
    [api, sessionId, thinkingIds, patchSession, onError],
  );

  return { sendMessage, stopMessage, isThinking };
}
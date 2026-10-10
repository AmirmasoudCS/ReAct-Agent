// The ONLY file that knows your backend's URLs and response shapes.
// Everything it returns is already in the shape the UI expects:
//
//   Session: { id, name, created_at, updated_at, message_count, messages? }
//   Message: { id, role: "user" | "assistant", content, activity: Activity[] }
//   Activity: { type: "planning" | "action" | "observation", ... }
//
// For a different backend, rewrite this file and leave the rest alone.

function normalizeMessages(messages = []) {
  return messages.map((message, index) => ({
    id: `${message.role}-${index}`,
    role: message.role,
    content: message.content,
    activity: message.activity ?? [],
  }));
}

function normalizeSession(session) {
  return { ...session, messages: normalizeMessages(session.messages) };
}

export function createAgentApi(http) {
  const sessionPath = (id) => `/sessions/${encodeURIComponent(id)}`;

  return {
    health: () => http.get("/health"),

    listSessions: () => http.get("/sessions"),

    getSession: async (id) => normalizeSession(await http.get(sessionPath(id))),

    createSession: async (name) =>
      normalizeSession(await http.post("/sessions", name ? { name } : {})),

    sendMessage: async (id, content) => {
      const result = await http.post(`${sessionPath(id)}/messages`, {
        content,
      });

      return {
        session: result.session,
        messages: normalizeMessages(result.messages),
        answer: result.answer,
      };
    },

    // Streams the agent's steps. onEvent receives each raw event:
    //   token, action, observation, final, error, done.
    // Resolves with the same shape as sendMessage once "done" arrives.
    streamMessage: async (id, content, { onEvent, signal } = {}) => {
      let done = null;

      await http.stream(`${sessionPath(id)}/messages/stream`, {
        body: { content },
        signal,
        onEvent: (event) => {
          if (event.type === "done") {
            done = {
              session: event.session,
              messages: normalizeMessages(event.messages),
              answer: event.answer,
            };
          }
          onEvent?.(event);
        },
      });

      if (!done) {
        throw new Error("The response ended before it completed.");
      }

      return done;
    },
  };
}
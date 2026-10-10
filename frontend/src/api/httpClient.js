// Generic JSON-over-HTTP client. Knows nothing about your agent.
// Copy this file into any project unchanged.

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    // status 0 means the server could not be reached at all.
    this.status = status;
  }
}

function extractMessage(data, status) {
  const detail = data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  // FastAPI validation errors (422) arrive as a list of { msg, loc, ... }.
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item.msg).filter(Boolean);
    if (messages.length) {
      return messages.join(" ");
    }
  }

  return `Request failed with status ${status}.`;
}

export function createHttpClient(baseUrl) {
  async function request(path, { method = "GET", body, signal } = {}) {
    let response;

    try {
      response = await fetch(`${baseUrl}${path}`, {
        method,
        signal,
        headers:
          body !== undefined ? { "Content-Type": "application/json" } : {},
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (error) {
      if (error.name === "AbortError") {
        throw error;
      }
      throw new ApiError("The server could not be reached.", 0);
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new ApiError(extractMessage(data, response.status), response.status);
    }

    return data;
  }

  // POST a JSON body and read the response as Server-Sent Events,
  // calling onEvent(parsedJson) for each event as it arrives.
  async function stream(path, { body, signal, onEvent }) {
    let response;

    try {
      response = await fetch(`${baseUrl}${path}`, {
        method: "POST",
        signal,
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify(body),
      });
    } catch (error) {
      if (error.name === "AbortError") {
        throw error;
      }
      throw new ApiError("The server could not be reached.", 0);
    }

    // Errors raised before streaming starts (404, 422, ...) are plain JSON.
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new ApiError(extractMessage(data, response.status), response.status);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        let chunk;

        // Only the read is wrapped, so errors thrown by onEvent
        // are not mistaken for a dropped connection.
        try {
          chunk = await reader.read();
        } catch (error) {
          if (error.name === "AbortError") {
            throw error;
          }
          throw new ApiError("The connection was interrupted.", 0);
        }

        if (chunk.done) {
          break;
        }

        buffer += decoder.decode(chunk.value, { stream: true });
        buffer = buffer.replace(/\r\n/g, "\n");

        let boundary;
        while ((boundary = buffer.indexOf("\n\n")) !== -1) {
          const rawEvent = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);

          const data = rawEvent
            .split("\n")
            .filter((line) => line.startsWith("data:"))
            .map((line) => line.slice(5).replace(/^ /, ""))
            .join("\n");

          if (data) {
            onEvent(JSON.parse(data));
          }
        }
      }
    } finally {
      reader.releaseLock?.();
    }
  }

  return {
    request,
    stream,
    get: (path, options) => request(path, { ...options, method: "GET" }),
    post: (path, body, options) =>
      request(path, { ...options, method: "POST", body }),
    patch: (path, body, options) =>
      request(path, { ...options, method: "PATCH", body }),
    delete: (path, options) => request(path, { ...options, method: "DELETE" }),
  };
}
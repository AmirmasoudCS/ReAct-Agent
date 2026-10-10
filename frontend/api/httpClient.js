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

  return {
    request,
    get: (path, options) => request(path, { ...options, method: "GET" }),
    post: (path, body, options) =>
      request(path, { ...options, method: "POST", body }),
    patch: (path, body, options) =>
      request(path, { ...options, method: "PATCH", body }),
    delete: (path, options) => request(path, { ...options, method: "DELETE" }),
  };
}
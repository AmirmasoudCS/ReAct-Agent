// The only place where environment-specific values live.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

export const APP_NAME = import.meta.env.VITE_APP_NAME ?? "ReAct Agent";
import { buildFetchInit, formatApiError } from "./http.js";

const API = import.meta.env.VITE_API_BASE || "";

export async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, buildFetchInit(options));
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(formatApiError(data));
  return data;
}

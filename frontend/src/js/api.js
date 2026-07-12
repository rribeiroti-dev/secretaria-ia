const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || "http://localhost:8000";

export function setTokens({ access_token, refresh_token }) {
  sessionStorage.setItem("access_token", access_token);
  sessionStorage.setItem("refresh_token", refresh_token);
}

export function clearTokens() {
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("refresh_token");
}

export function isAuthenticated() {
  return Boolean(sessionStorage.getItem("access_token"));
}

class ApiError extends Error {
  constructor(message, status, errors) {
    super(message);
    this.status = status;
    this.errors = errors;
  }
}

async function _request(path, { method = "GET", body, isFormData = false, auth = true, retry = true } = {}) {
  const headers = {};

  const currentAccessToken = sessionStorage.getItem("access_token");
  const currentRefreshToken = sessionStorage.getItem("refresh_token");

  if (!isFormData) headers["Content-Type"] = "application/json";
  if (auth && currentAccessToken) headers["Authorization"] = `Bearer ${currentAccessToken}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && auth && retry && currentRefreshToken) {
    const refreshed = await _tryRefresh(currentRefreshToken);
    if (refreshed) {
      return _request(path, { method, body, isFormData, auth, retry: false });
    }
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message = payload?.detail || "Ocorreu um erro inesperado. Tente novamente.";
    throw new ApiError(message, response.status, payload?.errors);
  }

  return payload;
}

async function _tryRefresh(refreshToken) {
  try {
    const result = await _request("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      auth: false,
      retry: false,
    });
    setTokens(result);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export const api = {
  register: (data) => _request("/auth/register", { method: "POST", body: data, auth: false }),
  login: (data) => _request("/auth/login", { method: "POST", body: data, auth: false }),
  verify2FA: (data) => _request("/auth/verify-2fa", { method: "POST", body: data, auth: false }),

  askChat: (question) => _request("/chat/ask", { method: "POST", body: { question } }),

  addTextMemory: (content) => _request("/memory/text", { method: "POST", body: { content } }),

  addMediaMemory: (kind, blob, filename) => {
    const form = new FormData();
    form.append("file", blob, filename);
    return _request(`/memory/${kind}`, { method: "POST", body: form, isFormData: true });
  },

  getHistory: (limit = 50, offset = 0) => _request(`/memory/history?limit=${limit}&offset=${offset}`),
};

export { ApiError };
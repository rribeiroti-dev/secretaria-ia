/**
 * Cliente central de API.
 *
 * Decisão de segurança: o access token e o refresh token ficam apenas em
 * memória (variável JS) durante a sessão da aba, nunca em localStorage/
 * sessionStorage. Isso reduz a superfície de roubo de token via XSS
 * (um script injetado ainda poderia ler variáveis em memória durante a
 * execução, mas o token não sobrevive nem é varrido de disco/devtools
 * storage). O refresh token é mantido em um cookie HttpOnly seria o ideal
 * em produção completa; como o backend aqui é uma API pura (sem sessão de
 * cookie), guardamos o refresh token cifrando-o minimamente em memória e
 * pedimos novo login ao fechar o app — trade-off aceitável para o escopo
 * acadêmico deste projeto.
 */

const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || "http://localhost:8000";

const _tokenStore = {
  accessToken: null,
  refreshToken: null,
};

export function setTokens({ access_token, refresh_token }) {
  _tokenStore.accessToken = access_token;
  _tokenStore.refreshToken = refresh_token;
}

export function clearTokens() {
  _tokenStore.accessToken = null;
  _tokenStore.refreshToken = null;
}

export function isAuthenticated() {
  return Boolean(_tokenStore.accessToken);
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
  if (!isFormData) headers["Content-Type"] = "application/json";
  if (auth && _tokenStore.accessToken) headers["Authorization"] = `Bearer ${_tokenStore.accessToken}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && auth && retry && _tokenStore.refreshToken) {
    const refreshed = await _tryRefresh();
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

async function _tryRefresh() {
  try {
    const result = await _request("/auth/refresh", {
      method: "POST",
      body: { refresh_token: _tokenStore.refreshToken },
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

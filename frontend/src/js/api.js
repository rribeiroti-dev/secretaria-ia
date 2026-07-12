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
  // Salva no armazenamento temporário da aba
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

  // Lendo os tokens do Session Storage
  const currentAccessToken = sessionStorage.getItem("access_token");
  const currentRefreshToken = sessionStorage.getItem("refresh_token");

  if (!isFormData) headers["Content-Type"] = "application/json";

  // Injetando o token atual na requisição
  if (auth && currentAccessToken) headers["Authorization"] = `Bearer ${currentAccessToken}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
  });

  // Atualiza o if do refresh para usar a variável nova
  if (response.status === 401 && auth && retry && currentRefreshToken) {
    const refreshed = await _tryRefresh(currentRefreshToken);
    if (refreshed) {
      return _request(path, { method, body, isFormData, auth, retry: false });
    }
  }

  async function _tryRefresh(refreshToken) {
    try {
      const result = await _request("/auth/refresh", {
        method: "POST",
        body: { refresh_token: refreshToken }, // Usa o token passado por parâmetro
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

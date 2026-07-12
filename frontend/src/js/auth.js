/**
 * Fluxo de autenticação (tela index.html): cadastro -> configuração do 2FA
 * -> login (senha) -> verificação do código do app autenticador -> app.html.
 *
 * Validação client-side aqui é só para UX (feedback rápido); a validação
 * que realmente importa para segurança acontece sempre no backend.
 */
import { api, setTokens, ApiError } from "./api.js";

const screens = {
  login: document.getElementById("screen-login"),
  register: document.getElementById("screen-register"),
  totpSetup: document.getElementById("screen-totp-setup"),
  twoFactor: document.getElementById("screen-2fa"),
};

let pending2FAToken = null;

function showScreen(name) {
  Object.values(screens).forEach((el) => el.classList.remove("active"));
  screens[name].classList.add("active");
}

function showError(formEl, message) {
  const box = formEl.querySelector(".form-error");
  box.textContent = message;
  box.style.display = message ? "flex" : "none";
}

function setLoading(button, loading, labelWhenIdle) {
  button.disabled = loading;
  button.innerHTML = loading ? '<span class="spinner"></span>' : labelWhenIdle;
}

// --- Navegação entre telas de login/cadastro ---
document.getElementById("go-to-register").addEventListener("click", () => showScreen("register"));
document.getElementById("go-to-login").addEventListener("click", () => showScreen("login"));

// --- Cadastro ---
const registerForm = document.getElementById("form-register");
registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError(registerForm, "");
  const submitBtn = registerForm.querySelector("button[type=submit]");

  const payload = {
    full_name: registerForm.full_name.value.trim(),
    email: registerForm.email.value.trim(),
    password: registerForm.password.value,
  };

  if (payload.password !== registerForm.password_confirm.value) {
    showError(registerForm, "As senhas não coincidem.");
    return;
  }

  setLoading(submitBtn, true);
  try {
    const result = await api.register(payload);
    _renderTotpSetup(result, payload.email);
    showScreen("totpSetup");
  } catch (err) {
    showError(registerForm, err instanceof ApiError ? err.message : "Não foi possível concluir o cadastro.");
  } finally {
    setLoading(submitBtn, false, "Criar conta");
  }
});

function _renderTotpSetup(result, email) {
  document.getElementById("totp-secret-text").textContent = result.totp_secret;
  const qrImg = document.getElementById("totp-qr");
  // Gera o QR code localmente (sem depender de serviço externo) usando a biblioteca leve carregada no HTML.
  qrImg.innerHTML = "";
  // eslint-disable-next-line no-undef
  new QRCode(qrImg, { text: result.totp_provisioning_uri, width: 200, height: 200 });

  document.getElementById("totp-setup-continue").onclick = () => {
    document.getElementById("login-email").value = email;
    showScreen("login");
  };
}

// --- Login (etapa 1: senha) ---
const loginForm = document.getElementById("form-login");
loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError(loginForm, "");
  const submitBtn = loginForm.querySelector("button[type=submit]");

  setLoading(submitBtn, true);
  try {
    const result = await api.login({
      email: loginForm.email.value.trim(),
      password: loginForm.password.value,
    });
    pending2FAToken = result.pending_2fa_token;
    document.getElementById("totp-code-input").value = "";
    showScreen("twoFactor");
    document.getElementById("totp-code-input").focus();
  } catch (err) {
    showError(loginForm, err instanceof ApiError ? err.message : "Não foi possível entrar.");
  } finally {
    setLoading(submitBtn, false, "Entrar");
  }
});

// --- Login (etapa 2: código do autenticador) ---
const twoFactorForm = document.getElementById("form-2fa");
twoFactorForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError(twoFactorForm, "");
  const submitBtn = twoFactorForm.querySelector("button[type=submit]");

  setLoading(submitBtn, true);
  try {
    const tokens = await api.verify2FA({
      pending_2fa_token: pending2FAToken,
      totp_code: twoFactorForm.totp_code.value.trim(),
    });
    setTokens(tokens);
    window.location.href = "app.html";
  } catch (err) {
    showError(twoFactorForm, err instanceof ApiError ? err.message : "Código inválido.");
  } finally {
    setLoading(submitBtn, false, "Confirmar e entrar");
  }
});

document.getElementById("back-to-login-from-2fa").addEventListener("click", () => showScreen("login"));

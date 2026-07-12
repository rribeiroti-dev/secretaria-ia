/** Controlador principal da tela autenticada: abas (chat/histórico) e logout. */
import { isAuthenticated, clearTokens } from "./api.js";
import { loadHistoryIfNeeded } from "./history.js";

// Guarda de rota simples: sem token em memória, volta para o login.
// (A validação que realmente protege os dados acontece no backend em cada
// requisição — isto é só uma conveniência de navegação no cliente.)
if (!isAuthenticated()) {
  window.location.href = "index.html";
}

const tabs = document.querySelectorAll(".tab-bar button");
const views = document.querySelectorAll(".view");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    views.forEach((v) => v.classList.remove("active"));

    tab.classList.add("active");
    document.getElementById(`view-${tab.dataset.view}`).classList.add("active");

    if (tab.dataset.view === "history") {
      loadHistoryIfNeeded();
    }
  });
});

document.getElementById("logout-button").addEventListener("click", () => {
  clearTokens();
  window.location.href = "index.html";
});

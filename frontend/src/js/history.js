/** Tela de histórico: lista tudo o que já foi registrado, com filtro por tipo. */
import { api, ApiError } from "./api.js";
import { showToast } from "./toast.js";

const listEl = document.getElementById("history-list");
const emptyEl = document.getElementById("history-empty-state");
const chips = document.querySelectorAll(".filter-chip");

const SOURCE_LABELS = {
  texto: "Texto",
  audio: "Áudio",
  foto: "Foto",
  video: "Vídeo",
};

let allItems = [];
let activeFilter = "todos";
let loaded = false;

function render() {
  const items = activeFilter === "todos" ? allItems : allItems.filter((i) => i.source_type === activeFilter);

  listEl.innerHTML = "";
  if (items.length === 0) {
    emptyEl.style.display = "flex";
    return;
  }
  emptyEl.style.display = "none";

  for (const item of items) {
    const row = document.createElement("div");
    row.className = "history-item";
    const date = new Date(item.created_at).toLocaleString("pt-BR");

    const badge = document.createElement("div");
    badge.className = "seal-badge";
    badge.setAttribute("aria-hidden", "true");
    badge.textContent = (SOURCE_LABELS[item.source_type] || "?")[0];

    const body = document.createElement("div");

    const meta = document.createElement("div");
    meta.className = "history-meta";
    meta.textContent = `${SOURCE_LABELS[item.source_type] || item.source_type} · ${date}${
      item.original_filename ? ` · ${item.original_filename}` : ""
    }`;

    const text = document.createElement("div");
    text.className = "history-text";
    text.textContent = item.extracted_text;

    body.append(meta, text);
    row.append(badge, body);
    listEl.appendChild(row);
  }
}

export async function loadHistoryIfNeeded() {
  if (loaded) return;
  try {
    const result = await api.getHistory(100, 0);
    allItems = result.items;
    loaded = true;
    render();
  } catch (err) {
    showToast(err instanceof ApiError ? err.message : "Não foi possível carregar o histórico.", "error");
  }
}

export function refreshHistory() {
  loaded = false;
  return loadHistoryIfNeeded();
}

chips.forEach((chip) => {
  chip.addEventListener("click", () => {
    chips.forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    activeFilter = chip.dataset.filter;
    render();
  });
});

// Dispara a atualização do histórico sempre que o botão da aba inferior for clicado
const historyTabButton = document.querySelector('button[data-view="history"]');
if (historyTabButton) {
  historyTabButton.addEventListener("click", () => {
    refreshHistory();
  });
}

// Carrega o histórico pela primeira vez se a aba já estiver ativa
loadHistoryIfNeeded();
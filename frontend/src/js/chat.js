/**
 * Tela de chat: composição de mensagens (texto ou mídia) e exibição das
 * respostas do agente, sempre deixando claro quando a resposta foi (ou não)
 * ancorada em algo que o usuário já registrou.
 */
import { api, ApiError } from "./api.js";
import { capturePhoto, recordAudio, recordVideo } from "./mediaCapture.js";
import { showToast } from "./toast.js";

const chatScroll = document.getElementById("chat-scroll");
const emptyState = document.getElementById("chat-empty-state");
const composerForm = document.getElementById("composer-form");
const textInput = document.getElementById("composer-input");
const mediaButton = document.getElementById("media-menu-toggle");
const mediaMenu = document.getElementById("media-menu");

const SOURCE_LABELS = {
  texto: "Texto",
  audio: "Áudio",
  foto: "Foto",
  video: "Vídeo",
};

function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function hideEmptyState() {
  if (emptyState) emptyState.style.display = "none";
}

function addBubble(text, role) {
  hideEmptyState();
  const bubble = document.createElement("div");
  bubble.className = `bubble bubble-${role}`;
  bubble.textContent = text;
  chatScroll.appendChild(bubble);
  scrollToBottom();
  return bubble;
}

function addAgentAnswer(answer, usedMemories, grounded) {
  hideEmptyState();
  const bubble = document.createElement("div");
  bubble.className = `bubble bubble-agent${grounded ? "" : " not-grounded"}`;
  bubble.textContent = answer;

  if (grounded && usedMemories?.length) {
    const sourcesEl = document.createElement("div");
    sourcesEl.className = "bubble-sources";
    usedMemories.forEach((mem) => {
      const chip = document.createElement("span");
      chip.className = "source-chip";
      chip.textContent = `${SOURCE_LABELS[mem.source_type] || mem.source_type} · ${new Date(mem.created_at).toLocaleDateString("pt-BR")}`;
      sourcesEl.appendChild(chip);
    });
    bubble.appendChild(sourcesEl);
  }

  chatScroll.appendChild(bubble);
  scrollToBottom();
}

function addTypingIndicator() {
  hideEmptyState();
  const el = document.createElement("div");
  el.className = "typing-indicator";
  el.id = "typing-indicator";
  el.innerHTML = "<span></span><span></span><span></span>";
  chatScroll.appendChild(el);
  scrollToBottom();
  return el;
}

function removeTypingIndicator() {
  document.getElementById("typing-indicator")?.remove();
}

async function sendQuestion(question) {
  addBubble(question, "user");
  const typing = addTypingIndicator();
  try {
    const result = await api.askChat(question);
    typing.remove();
    addAgentAnswer(result.answer, result.used_memories, result.grounded);
  } catch (err) {
    typing.remove();
    addAgentAnswer(
      err instanceof ApiError ? err.message : "Não consegui responder agora. Tente novamente.",
      [],
      false
    );
  }
}

async function registerTextMemory(text) {
  hideEmptyState();
  const savingBubble = addBubble(text, "user");
  const typing = addTypingIndicator();
  try {
    // Esta é a magia: chama a rota correta do seu api.js para GUARDAR texto
    await api.addTextMemory(text);
    typing.remove();
    addAgentAnswer(`Anotado! Acabei de guardar essa informação na sua memória pessoal.`, [], true);
    showToast("Texto registado com sucesso!", "success");
  } catch (err) {
    typing.remove();
    savingBubble.remove();
    showToast(err instanceof ApiError ? err.message : "Não foi possível guardar o texto.", "error");
  }
}

composerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = textInput.value.trim();
  if (!value) return;
  textInput.value = "";
  textInput.style.height = "auto";

  const textLower = value.toLowerCase();

  // Heurística de intenção: Se usar comandos ou palavras-chave, nós guardamos na base de dados!
  if (textLower.startsWith("/guardar") ||
    textLower.startsWith("/gravar") ||
    textLower.startsWith("lembre-se que") ||
    textLower.startsWith("anote que")) {

    // Remove a palavra de comando para guardar apenas a informação útil
    let textToSave = value.replace(/^\/(guardar|gravar)\s*/i, "");
    textToSave = textToSave.replace(/^(lembre-se que|anote que)\s*/i, "");

    // Chama a nova função que vai efetivamente salvar a memória
    await registerTextMemory(textToSave);
  } else {
    // Caso contrário, trata a frase como uma pergunta/consulta normal
    await sendQuestion(value);
  }
});

textInput.addEventListener("input", () => {
  textInput.style.height = "auto";
  textInput.style.height = `${Math.min(textInput.scrollHeight, 120)}px`;
});

// --- Menu de mídia (foto / vídeo / áudio / anexar arquivo) ---
mediaButton.addEventListener("click", (e) => {
  e.stopPropagation();
  mediaMenu.hidden = !mediaMenu.hidden;
});
document.addEventListener("click", () => {
  mediaMenu.hidden = true;
});

async function registerMemoryFromBlob(kind, blob, filename, successLabel) {
  hideEmptyState();
  const savingBubble = addBubble(`Processando ${successLabel.toLowerCase()}…`, "user");
  const typing = addTypingIndicator();
  try {
    const result = await api.addMediaMemory(kind, blob, filename);
    typing.remove();
    savingBubble.remove();
    addBubble(`${successLabel} enviado(a).`, "user");
    addAgentAnswer(`Anotado! ${result.memory.extracted_text.slice(0, 240)}${result.memory.extracted_text.length > 240 ? "…" : ""}`, [], true);
    showToast(result.message, "success");
  } catch (err) {
    typing.remove();
    savingBubble.remove();
    showToast(err instanceof ApiError ? err.message : "Não foi possível processar o arquivo.", "error");
  }
}

document.getElementById("action-take-photo").addEventListener("click", async () => {
  mediaMenu.hidden = true;
  try {
    const blob = await capturePhoto();
    await registerMemoryFromBlob("image", blob, "foto.jpg", "Foto");
  } catch (err) {
    if (err.message !== "cancelled") showToast("Não foi possível acessar a câmera.", "error");
  }
});

document.getElementById("action-record-video").addEventListener("click", async () => {
  mediaMenu.hidden = true;
  try {
    const blob = await recordVideo();
    await registerMemoryFromBlob("video", blob, "video.webm", "Vídeo");
  } catch (err) {
    if (err.message !== "cancelled") showToast("Não foi possível acessar a câmera.", "error");
  }
});

document.getElementById("action-record-audio").addEventListener("click", async () => {
  mediaMenu.hidden = true;
  try {
    const blob = await recordAudio();
    await registerMemoryFromBlob("audio", blob, "audio.webm", "Áudio");
  } catch (err) {
    if (err.message !== "cancelled") showToast("Não foi possível acessar o microfone.", "error");
  }
});

document.getElementById("action-attach-file").addEventListener("click", () => {
  mediaMenu.hidden = true;
  document.getElementById("file-input").click();
});

document.getElementById("file-input").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;

  let kind;
  if (file.type.startsWith("audio/")) kind = "audio";
  else if (file.type.startsWith("image/")) kind = "image";
  else if (file.type.startsWith("video/")) kind = "video";
  else {
    showToast("Tipo de arquivo não suportado. Envie áudio, foto ou vídeo.", "error");
    return;
  }

  await registerMemoryFromBlob(kind, file, file.name, "Arquivo");
});

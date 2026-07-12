/** Notificações discretas (toast) reutilizadas em todo o app autenticado. */
let stack = null;

function getStack() {
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "toast-stack";
    document.body.appendChild(stack);
  }
  return stack;
}

export function showToast(message, type = "success", durationMs = 3200) {
  const container = getStack();
  const toast = document.createElement("div");
  toast.className = `toast alert alert-${type === "error" ? "error" : "success"}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), durationMs);
}

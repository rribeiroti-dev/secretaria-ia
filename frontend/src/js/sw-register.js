/** Registra o service worker para permitir instalação e uso como PWA. */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch((err) => {
      console.warn("Falha ao registrar o service worker:", err);
    });
  });
}

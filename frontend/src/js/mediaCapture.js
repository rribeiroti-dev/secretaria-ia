/**
 * Captura nativa de mídia via APIs do navegador (getUserMedia + MediaRecorder).
 *
 * Segurança/privacidade: a câmera e o microfone só são ativados quando o
 * usuário explicitamente escolhe "tirar foto", "gravar vídeo" ou "gravar
 * áudio". O stream é sempre parado (todas as tracks encerradas) assim que
 * a captura termina ou é cancelada — nunca fica ativo em segundo plano.
 */

let _activeStream = null;

function _stopActiveStream() {
  if (_activeStream) {
    _activeStream.getTracks().forEach((track) => track.stop());
    _activeStream = null;
  }
}

function _buildOverlay({ title, showVideo }) {
  const overlay = document.createElement("div");
  overlay.className = "capture-overlay";
  overlay.innerHTML = `
    <p style="color:#fff; font-family: var(--font-body); margin:0;">${title}</p>
    ${showVideo ? '<video autoplay playsinline muted></video>' : '<div class="record-timer" id="capture-timer">00:00</div>'}
    <div class="capture-controls" id="capture-controls"></div>
  `;
  document.body.appendChild(overlay);
  return overlay;
}

function _removeOverlay(overlay) {
  _stopActiveStream();
  overlay.remove();
}

function _formatTime(totalSeconds) {
  const m = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const s = String(totalSeconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

/** Captura uma foto usando a câmera traseira por padrão. Retorna um Blob JPEG. */
export async function capturePhoto() {
  const overlay = _buildOverlay({ title: "Enquadre a foto e capture", showVideo: true });
  const videoEl = overlay.querySelector("video");
  const controls = overlay.querySelector("#capture-controls");

  try {
    _activeStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
      audio: false,
    });
    videoEl.srcObject = _activeStream;

    return await new Promise((resolve, reject) => {
      const shootBtn = document.createElement("button");
      shootBtn.className = "btn btn-primary btn-icon";
      shootBtn.setAttribute("aria-label", "Capturar foto");
      shootBtn.textContent = "●";

      const cancelBtn = document.createElement("button");
      cancelBtn.className = "btn btn-secondary";
      cancelBtn.textContent = "Cancelar";
      cancelBtn.style.background = "#fff";

      controls.append(cancelBtn, shootBtn);

      cancelBtn.onclick = () => {
        _removeOverlay(overlay);
        reject(new Error("cancelled"));
      };

      shootBtn.onclick = () => {
        const canvas = document.createElement("canvas");
        canvas.width = videoEl.videoWidth;
        canvas.height = videoEl.videoHeight;
        canvas.getContext("2d").drawImage(videoEl, 0, 0);
        canvas.toBlob(
          (blob) => {
            _removeOverlay(overlay);
            resolve(blob);
          },
          "image/jpeg",
          0.9
        );
      };
    });
  } catch (err) {
    _removeOverlay(overlay);
    throw err;
  }
}

/** Grava áudio pelo microfone. Retorna um Blob (audio/webm). */
export function recordAudio() {
  return _recordWithRecorder({
    title: "Gravando áudio — toque para parar",
    constraints: { audio: true, video: false },
    mimeType: "audio/webm",
    showVideo: false,
  });
}

/** Grava vídeo pela câmera. Retorna um Blob (video/webm). */
export function recordVideo() {
  return _recordWithRecorder({
    title: "Gravando vídeo — toque para parar",
    constraints: { audio: true, video: { facingMode: "environment" } },
    mimeType: "video/webm",
    showVideo: true,
  });
}

async function _recordWithRecorder({ title, constraints, mimeType, showVideo }) {
  const overlay = _buildOverlay({ title, showVideo });
  const controls = overlay.querySelector("#capture-controls");
  const videoEl = overlay.querySelector("video");
  const timerEl = overlay.querySelector("#capture-timer");

  try {
    _activeStream = await navigator.mediaDevices.getUserMedia(constraints);
    if (showVideo && videoEl) videoEl.srcObject = _activeStream;

    const recorder = new MediaRecorder(_activeStream, { mimeType });
    const chunks = [];
    recorder.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data);

    let seconds = 0;
    const interval = setInterval(() => {
      seconds += 1;
      if (timerEl) timerEl.textContent = _formatTime(seconds);
    }, 1000);

    return await new Promise((resolve, reject) => {
      const stopBtn = document.createElement("button");
      stopBtn.className = "btn btn-primary btn-icon";
      stopBtn.innerHTML = '<span class="record-dot"></span>';
      stopBtn.setAttribute("aria-label", "Parar gravação");

      const cancelBtn = document.createElement("button");
      cancelBtn.className = "btn btn-secondary";
      cancelBtn.textContent = "Cancelar";
      cancelBtn.style.background = "#fff";

      controls.append(cancelBtn, stopBtn);

      let cancelled = false;

      cancelBtn.onclick = () => {
        cancelled = true;
        clearInterval(interval);
        recorder.stop();
      };

      stopBtn.onclick = () => {
        clearInterval(interval);
        recorder.stop();
      };

      recorder.onstop = () => {
        _removeOverlay(overlay);
        if (cancelled) {
          reject(new Error("cancelled"));
          return;
        }
        const blob = new Blob(chunks, { type: mimeType });
        resolve(blob);
      };

      recorder.start();
    });
  } catch (err) {
    _removeOverlay(overlay);
    throw err;
  }
}

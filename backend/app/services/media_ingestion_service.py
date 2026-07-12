"""
Ingestão multimodal: recebe bytes de áudio, foto ou vídeo, valida
tipo/tamanho (segurança) e devolve o texto extraído para indexação na memória.

Vídeo é tratado extraindo um frame-chave (para descrição visual) e a trilha
de áudio (para transcrição), via ffmpeg. Isso evita depender de um modelo
multimodal de vídeo nativo, que raramente está disponível nas camadas free.
"""
import logging
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.services import llm_service

logger = logging.getLogger("media_ingestion_service")


async def _read_and_validate(file: UploadFile, allowed_types: list[str]) -> bytes:
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    if file.content_type not in allowed_types:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Tipo de arquivo não suportado: {file.content_type}.",
        )

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Arquivo excede o limite de {settings.max_upload_size_mb}MB.",
        )
    if len(content) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arquivo vazio.")

    return content


async def process_audio(file: UploadFile) -> str:
    settings = get_settings()
    allowed = settings.allowed_audio_types.split(",")
    content = await _read_and_validate(file, allowed)
    text = await llm_service.transcribe_audio(content, file.filename or "audio", file.content_type)
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Não foi possível identificar fala no áudio enviado.")
    return text


async def process_image(file: UploadFile) -> str:
    settings = get_settings()
    allowed = settings.allowed_image_types.split(",")
    content = await _read_and_validate(file, allowed)
    return await llm_service.describe_image(content, file.content_type)


async def process_video(file: UploadFile) -> str:
    settings = get_settings()
    allowed = settings.allowed_video_types.split(",")
    content = await _read_and_validate(file, allowed)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        video_path = tmp_path / "input_video"
        video_path.write_bytes(content)

        frame_path = tmp_path / "frame.jpg"
        audio_path = tmp_path / "audio.wav"

        frame_ok = _extract_frame(video_path, frame_path)
        audio_ok = _extract_audio(video_path, audio_path)

        description_parts: list[str] = []

        if frame_ok and frame_path.exists():
            image_bytes = frame_path.read_bytes()
            visual_description = await llm_service.describe_image(image_bytes, "image/jpeg")
            description_parts.append(f"Cena do vídeo: {visual_description}")

        if audio_ok and audio_path.exists() and audio_path.stat().st_size > 0:
            audio_bytes = audio_path.read_bytes()
            transcript = await llm_service.transcribe_audio(audio_bytes, "audio.wav", "audio/wav")
            if transcript:
                description_parts.append(f"Fala no vídeo: {transcript}")

        if not description_parts:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Não foi possível extrair conteúdo (imagem ou fala) do vídeo enviado.",
            )

        return "\n".join(description_parts)


def _extract_frame(video_path: Path, output_path: Path) -> bool:
    """Extrai um frame no segundo 1 do vídeo. Requer ffmpeg instalado no ambiente de execução."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "00:00:01", "-i", str(video_path), "-frames:v", "1", str(output_path)],
            check=True,
            capture_output=True,
            timeout=20,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("Falha ao extrair frame do vídeo: %s", exc)
        return False


def _extract_audio(video_path: Path, output_path: Path) -> bool:
    """Extrai a trilha de áudio do vídeo em WAV mono 16kHz (formato ideal para Whisper)."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(output_path)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("Falha ao extrair áudio do vídeo: %s", exc)
        return False

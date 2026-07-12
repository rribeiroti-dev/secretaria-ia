"""
Integração com provedores de IA externos (somente camadas free tier):

- Groq: transcrição de áudio (Whisper) — muito rápido no free tier.
- OpenRouter: chat de texto e descrição de imagem (modelos marcados ":free").

Toda chamada tem timeout definido e trata falhas sem vazar detalhes internos
ao usuário final (mensagens genéricas; detalhe completo só em log de servidor).
As chaves de API nunca são expostas ao frontend — ficam só nestes headers,
montados no backend a partir de variáveis de ambiente.
"""
import base64
import logging

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger("llm_service")

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_UPSTREAM_ERROR = HTTPException(
    status_code=status.HTTP_502_BAD_GATEWAY,
    detail="Não foi possível processar essa solicitação com o provedor de IA no momento. Tente novamente em instantes.",
)


async def transcribe_audio(audio_bytes: bytes, filename: str, content_type: str) -> str:
    """Transcreve áudio para texto usando o Whisper gratuito da Groq."""
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Serviço de transcrição não configurado.")

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    files = {"file": (filename, audio_bytes, content_type)}
    data = {"model": settings.groq_whisper_model, "language": "pt", "response_format": "json"}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        return response.json().get("text", "").strip()
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.error("Falha na transcrição de áudio: %s", exc)
        raise _UPSTREAM_ERROR from exc


async def describe_image(image_bytes: bytes, content_type: str) -> str:
    """Gera uma descrição textual da imagem usando um modelo de visão gratuito via OpenRouter."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Serviço de análise de imagem não configurado.")

    encoded = base64.b64encode(image_bytes).decode()
    data_url = f"data:{content_type};base64,{encoded}"

    payload = {
        "model": settings.llm_vision_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Descreva esta imagem em português do Brasil, de forma objetiva e detalhada, "
                            "incluindo qualquer texto visível (transcreva-o literalmente se houver)."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": 500,
    }

    return await _call_openrouter_chat(payload)


async def generate_grounded_answer(system_prompt: str, user_question: str) -> str:
    """Gera a resposta do agente restrita ao contexto fornecido no system_prompt."""
    settings = get_settings()
    payload = {
        "model": settings.llm_chat_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ],
        "max_tokens": 700,
        "temperature": 0.2,  # baixa temperatura: prioriza fidelidade ao contexto sobre criatividade
    }
    return await _call_openrouter_chat(payload)


async def _call_openrouter_chat(payload: dict) -> str:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Serviço de IA de texto não configurado.")

    url = f"{settings.openrouter_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()
        return body["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        logger.error("Falha na chamada ao OpenRouter: %s", exc)
        raise _UPSTREAM_ERROR from exc

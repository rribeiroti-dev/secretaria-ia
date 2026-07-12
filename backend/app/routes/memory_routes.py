from fastapi import APIRouter, Depends, Query, Request, UploadFile
from starlette import status

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, get_current_user
from app.middleware.rate_limit import limiter
from app.models.memory_schemas import (
    HistoryResponse,
    MemoryIngestResponse,
    SourceType,
    TextMemoryRequest,
)
from app.services import media_ingestion_service
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["memória"])
settings = get_settings()


def _service() -> MemoryService:
    return MemoryService()


@router.post("/text", response_model=MemoryIngestResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_media)
async def add_text_memory(request: Request, payload: TextMemoryRequest, user: CurrentUser = Depends(get_current_user)):
    """Registra uma informação em texto na memória do usuário autenticado."""
    memory = await _service().ingest_text(user.user_id, payload.content)
    return MemoryIngestResponse(message="Informação registrada na sua memória.", memory=memory)


@router.post("/audio", response_model=MemoryIngestResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_media)
async def add_audio_memory(request: Request, file: UploadFile, user: CurrentUser = Depends(get_current_user)):
    """Transcreve um áudio (gravado ou anexado) e registra o texto resultante na memória."""
    extracted_text = await media_ingestion_service.process_audio(file)
    memory = await _service().ingest_extracted_content(user.user_id, SourceType.AUDIO, extracted_text, file.filename)
    return MemoryIngestResponse(message="Áudio transcrito e registrado na sua memória.", memory=memory)


@router.post("/image", response_model=MemoryIngestResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_media)
async def add_image_memory(request: Request, file: UploadFile, user: CurrentUser = Depends(get_current_user)):
    """Descreve uma foto (capturada ou anexada) e registra a descrição na memória."""
    extracted_text = await media_ingestion_service.process_image(file)
    memory = await _service().ingest_extracted_content(user.user_id, SourceType.IMAGE, extracted_text, file.filename)
    return MemoryIngestResponse(message="Foto analisada e registrada na sua memória.", memory=memory)


@router.post("/video", response_model=MemoryIngestResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_media)
async def add_video_memory(request: Request, file: UploadFile, user: CurrentUser = Depends(get_current_user)):
    """Processa um vídeo (capturado ou anexado): extrai cena e fala, e registra na memória."""
    extracted_text = await media_ingestion_service.process_video(file)
    memory = await _service().ingest_extracted_content(user.user_id, SourceType.VIDEO, extracted_text, file.filename)
    return MemoryIngestResponse(message="Vídeo processado e registrado na sua memória.", memory=memory)


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    user: CurrentUser = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Lista o histórico de memórias já registradas pelo usuário autenticado, paginado."""
    items, total = await _service().list_history(user.user_id, limit=limit, offset=offset)
    return HistoryResponse(items=items, total=total)

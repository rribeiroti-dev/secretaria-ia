from fastapi import APIRouter, Depends, Request

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, get_current_user
from app.middleware.rate_limit import limiter
from app.models.memory_schemas import ChatRequest, ChatResponse
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()


@router.post("/ask", response_model=ChatResponse)
@limiter.limit(settings.rate_limit_chat)
async def ask(request: Request, payload: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    """
    Responde a uma pergunta do usuário usando exclusivamente a memória dele.
    Se não houver nenhuma informação relacionada já registrada, o agente
    informa isso claramente em vez de responder com conhecimento externo.
    """
    service = MemoryService()
    answer, used_memories, grounded = await service.answer_question(user.user_id, payload.question)
    return ChatResponse(answer=answer, used_memories=used_memories, grounded=grounded)

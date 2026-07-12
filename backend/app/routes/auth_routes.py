from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.middleware.rate_limit import limiter
from app.models.auth_schemas import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    Verify2FARequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["autenticação"])
settings = get_settings()


def _service() -> AuthService:
    return AuthService()


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit(settings.rate_limit_auth)
async def register(request: Request, payload: RegisterRequest):
    """Cria a conta e devolve o QR/segredo TOTP para configurar o 2FA. Nenhum acesso é concedido ainda."""
    return await _service().register(payload)


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.rate_limit_auth)
async def login(request: Request, payload: LoginRequest):
    """Primeira etapa do login: valida e-mail e senha. Não concede token de acesso."""
    return await _service().login(payload)


@router.post("/verify-2fa", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_auth)
async def verify_2fa(request: Request, payload: Verify2FARequest):
    """Segunda etapa do login: valida o código do app autenticador e emite os tokens de acesso."""
    return await _service().verify_2fa(payload)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_auth)
async def refresh(request: Request, payload: RefreshRequest):
    """Renova o access token usando um refresh token válido."""
    return await _service().refresh(payload.refresh_token)

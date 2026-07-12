"""
Ponto de entrada da API — Agente Secretária Particular.

Segurança aplicada nesta camada:
- CORS restrito exclusivamente às origens configuradas em ALLOWED_ORIGINS
  (o domínio do frontend publicado no Netlify), nunca "*".
- Rate limiting global via slowapi.
- Cabeçalhos de segurança HTTP em toda resposta.
- Tratamento de erro genérico: exceptions não previstas nunca vazam stack
  trace ou detalhes internos para o cliente.
"""
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.middleware.rate_limit import limiter
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routes import auth_routes, chat_routes, memory_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("secretaria_particular")

settings = get_settings()

app = FastAPI(
    title="Agente Secretária Particular — API",
    description="API do agente pessoal multimodal com memória restrita ao histórico do usuário.",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,  # esconde Swagger em produção
    redoc_url=None,
)

# --- Rate limiting global ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Cabeçalhos de segurança ---
app.add_middleware(SecurityHeadersMiddleware)

# --- CORS: apenas as origens explicitamente configuradas ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# --- Tratamento global de erros ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # exc.errors() pode conter, na chave "ctx", o objeto de exceção Python
    # original (ex.: ValueError levantado por um @field_validator). Esse
    # objeto não é serializável em JSON, então removemos "ctx" e mantemos
    # apenas "msg" (que já traz a mensagem legível para o usuário).
    sanitized_errors = [{k: v for k, v in error.items() if k != "ctx"} for error in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Dados inválidos.", "errors": sanitized_errors},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro não tratado: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno. Tente novamente em instantes."},
    )


# --- Rotas ---
app.include_router(auth_routes.router)
app.include_router(memory_routes.router)
app.include_router(chat_routes.router)


@app.get("/health", tags=["infra"])
async def health_check():
    """Healthcheck simples usado pelo Render para monitorar o serviço."""
    return {"status": "ok"}

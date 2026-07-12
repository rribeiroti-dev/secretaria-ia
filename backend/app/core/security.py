"""
Primitivas de segurança da aplicação:
- Hashing de senha (Argon2, via passlib) — nunca senha em texto plano.
- Emissão e validação de JWT de acesso/refresh, com expiração curta.
- Geração e verificação de códigos TOTP para autenticação de dois fatores.

Nenhum segredo é hardcoded: tudo vem de app.core.config.Settings (variáveis de ambiente).
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
import pyotp
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Argon2 é o algoritmo recomendado atualmente (mais resistente que bcrypt a GPU-cracking).
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ---------------------------------------------------------------------------
# Senhas
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Gera o hash seguro de uma senha. Nunca armazenar a senha original."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara a senha informada com o hash armazenado, em tempo constante."""
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT (access + refresh token)
# ---------------------------------------------------------------------------
TokenType = Literal["access", "refresh"]


def create_token(subject: str, token_type: TokenType, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Cria um JWT assinado.
    - access: vida curta, usado em toda requisição autenticada.
    - refresh: vida mais longa, usado apenas para renovar o access token.
    """
    now = datetime.now(timezone.utc)
    if token_type == "access":
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    else:
        expire = now + timedelta(days=settings.refresh_token_expire_days)

    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_hex(16),  # identificador único do token (permite revogação futura)
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decodifica e valida um JWT. Lança jwt.PyJWTError se inválido/expirado/adulterado.
    O chamador (dependency do FastAPI) é responsável por traduzir a exceção em HTTP 401.
    """
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


# ---------------------------------------------------------------------------
# TOTP — Autenticação de dois fatores (2FA)
# ---------------------------------------------------------------------------
def generate_totp_secret() -> str:
    """Gera um segredo TOTP novo para um usuário (armazenar de forma criptografada)."""
    return pyotp.random_base32()


def build_totp_provisioning_uri(secret: str, account_email: str, issuer: str = "Secretaria Particular IA") -> str:
    """
    Monta a URI otpauth:// usada para gerar o QR code que o usuário escaneia
    em um app autenticador (Google Authenticator, Authy, etc.).
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(name=account_email, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    """Verifica se o código de 6 dígitos informado é válido para o segredo do usuário."""
    totp = pyotp.TOTP(secret)
    # valid_window=1 tolera pequena diferença de relógio (±30s) sem abrir brecha maior
    return totp.verify(code, valid_window=1)


def generate_temp_2fa_token(user_id: str) -> str:
    """
    Token de curtíssima duração emitido após validar login (senha correta) mas
    antes do 2FA ser confirmado. Não serve como token de acesso à API.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "pending_2fa",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

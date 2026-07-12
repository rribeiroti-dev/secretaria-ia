"""
Dependências reutilizáveis do FastAPI.

`get_current_user` é a barreira de autenticação: toda rota sensível deve
declarar essa dependência. A verificação acontece sempre no servidor —
o frontend nunca é responsável por decidir se o acesso é permitido.
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token

_bearer_scheme = HTTPBearer(auto_error=True)


class CurrentUser:
    """Representa o usuário autenticado extraído do access token."""

    def __init__(self, user_id: str):
        self.user_id = user_id


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> CurrentUser:
    """
    Valida o access token JWT enviado no header Authorization: Bearer <token>.
    Rejeita tokens ausentes, expirados, adulterados ou que não sejam do tipo 'access'.
    """
    token = credentials.credentials
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise unauthorized
    except jwt.PyJWTError:
        raise unauthorized

    if payload.get("type") != "access":
        raise unauthorized

    user_id = payload.get("sub")
    if not user_id:
        raise unauthorized

    return CurrentUser(user_id=user_id)

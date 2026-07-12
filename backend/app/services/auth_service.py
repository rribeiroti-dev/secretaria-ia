"""
Regras de negócio de autenticação: cadastro, login (senha) e confirmação 2FA.

Fluxo de login em duas etapas, obrigatório para toda conta:
1. POST /auth/login  -> valida e-mail + senha. Se corretos, devolve um
   `pending_2fa_token` de curtíssima duração (5 min). Não concede acesso.
2. POST /auth/verify-2fa -> valida o código TOTP contra esse token pendente.
   Só então são emitidos o access_token e o refresh_token reais.
"""
import jwt
from fastapi import HTTPException, status

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.security import (
    build_totp_provisioning_uri,
    create_token,
    decode_token,
    generate_temp_2fa_token,
    generate_totp_secret,
    hash_password,
    verify_password,
    verify_totp_code,
)
from app.models.auth_schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    Verify2FARequest,
)
from app.repositories.user_repository import UserRepository

_MAX_FAILED_ATTEMPTS = 5


class AuthService:
    def __init__(self):
        self._users = UserRepository()

    def register(self, data: RegisterRequest) -> RegisterResponse:
        if self._users.get_by_email(data.email):
            # Mensagem genérica: não revela se o e-mail já existe em detalhe,
            # mas aqui optamos por clareza de UX; ajuste conforme política de privacidade.
            raise HTTPException(status.HTTP_409_CONFLICT, "Não foi possível concluir o cadastro com esses dados.")

        password_hash = hash_password(data.password)
        totp_secret = generate_totp_secret()
        encrypted_secret = encrypt_secret(totp_secret)

        self._users.create(
            email=data.email,
            full_name=data.full_name,
            password_hash=password_hash,
            totp_secret_encrypted=encrypted_secret,
        )

        provisioning_uri = build_totp_provisioning_uri(totp_secret, data.email)
        return RegisterResponse(
            message="Cadastro realizado. Configure seu aplicativo autenticador antes do primeiro login.",
            totp_provisioning_uri=provisioning_uri,
            totp_secret=totp_secret,
        )

    def login(self, data: LoginRequest) -> LoginResponse:
        user = self._users.get_by_email(data.email)
        generic_error = HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos.")

        if not user:
            # Não diferenciar "usuário não existe" de "senha errada" evita
            # enumeração de contas por um atacante.
            raise generic_error

        if user.get("failed_login_attempts", 0) >= _MAX_FAILED_ATTEMPTS:
            raise HTTPException(
                status.HTTP_423_LOCKED,
                "Conta temporariamente bloqueada por excesso de tentativas. Contate o suporte.",
            )

        if not verify_password(data.password, user["password_hash"]):
            self._users.register_failed_login(user["id"], user.get("failed_login_attempts", 0) + 1)
            raise generic_error

        self._users.reset_failed_login(user["id"])

        pending_token = generate_temp_2fa_token(user_id=user["id"])
        return LoginResponse(
            message="Senha confirmada. Informe o código do aplicativo autenticador para concluir o login.",
            pending_2fa_token=pending_token,
        )

    def verify_2fa(self, data: Verify2FARequest) -> TokenResponse:
        invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Código de verificação inválido ou expirado.")
        try:
            payload = decode_token(data.pending_2fa_token)
        except jwt.PyJWTError:
            raise invalid

        if payload.get("type") != "pending_2fa":
            raise invalid

        user_id = payload["sub"]
        user = self._users.get_by_id(user_id)
        if not user:
            raise invalid

        totp_secret = decrypt_secret(user["totp_secret_encrypted"])
        if not verify_totp_code(totp_secret, data.totp_code):
            raise invalid

        if not user.get("totp_confirmed"):
            self._users.confirm_totp(user_id)

        access_token = create_token(subject=user_id, token_type="access")
        refresh_token = create_token(subject=user_id, token_type="refresh")
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    def refresh(self, refresh_token: str) -> TokenResponse:
        invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Faça login novamente.")
        try:
            payload = decode_token(refresh_token)
        except jwt.PyJWTError:
            raise invalid

        if payload.get("type") != "refresh":
            raise invalid

        user_id = payload["sub"]
        new_access = create_token(subject=user_id, token_type="access")
        new_refresh = create_token(subject=user_id, token_type="refresh")
        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

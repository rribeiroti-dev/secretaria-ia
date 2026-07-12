"""Schemas Pydantic de entrada/saída para o fluxo de autenticação + 2FA."""
import re

from pydantic import BaseModel, EmailStr, field_validator

_PASSWORD_MIN_LENGTH = 10


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < _PASSWORD_MIN_LENGTH:
            raise ValueError(f"A senha deve ter pelo menos {_PASSWORD_MIN_LENGTH} caracteres.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("A senha deve conter ao menos uma letra maiúscula.")
        if not re.search(r"[a-z]", value):
            raise ValueError("A senha deve conter ao menos uma letra minúscula.")
        if not re.search(r"\d", value):
            raise ValueError("A senha deve conter ao menos um número.")
        if not re.search(r"[^\w\s]", value):
            raise ValueError("A senha deve conter ao menos um caractere especial.")
        return value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Informe um nome válido.")
        return cleaned


class RegisterResponse(BaseModel):
    message: str
    totp_provisioning_uri: str
    totp_secret: str  # exibido uma única vez para o usuário configurar o app autenticador


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Resposta intermediária: senha correta, mas 2FA ainda precisa ser confirmado."""
    message: str
    pending_2fa_token: str
    requires_2fa: bool = True


class Verify2FARequest(BaseModel):
    pending_2fa_token: str
    totp_code: str

    @field_validator("totp_code")
    @classmethod
    def validate_code_format(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError("O código de verificação deve conter exatamente 6 dígitos.")
        return value


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str

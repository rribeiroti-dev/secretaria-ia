"""
Criptografia simétrica (Fernet/AES) para dados sensíveis em repouso.

Usado para armazenar o segredo TOTP de cada usuário de forma cifrada no
banco — mesmo que o banco vaze, o segredo do 2FA não fica em texto plano.
A chave (TOTP_ENCRYPTION_KEY) é gerada uma vez com Fernet.generate_key()
e guardada apenas como variável de ambiente, nunca no código-fonte.
"""
from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import get_settings


@lru_cache
def _get_fernet() -> Fernet:
    settings = get_settings()
    key = getattr(settings, "totp_encryption_key", None)
    if not key:
        raise RuntimeError(
            "TOTP_ENCRYPTION_KEY não configurada. Gere uma com "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "e defina como variável de ambiente."
        )
    return Fernet(key.encode())


def encrypt_secret(plain_text: str) -> str:
    return _get_fernet().encrypt(plain_text.encode()).decode()


def decrypt_secret(cipher_text: str) -> str:
    return _get_fernet().decrypt(cipher_text.encode()).decode()

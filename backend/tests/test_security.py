"""
Testes unitários das primitivas de segurança.
Rodar com: pytest (a partir da pasta backend/, com o .env configurado).
"""
import os
import time

os.environ.setdefault("JWT_SECRET_KEY", "chave-de-teste-nao-usar-em-producao")
os.environ.setdefault("TOTP_ENCRYPTION_KEY", "wTQb9x0h7v3D2sV5s1v0mYb0y2m9dQe9F8lQe2m9dQ8=")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5500")

import jwt
import pytest

from app.core.security import (
    create_token,
    decode_token,
    generate_totp_secret,
    hash_password,
    verify_password,
    verify_totp_code,
)


def test_password_hash_is_never_plain_text():
    hashed = hash_password("SenhaForte123!")
    assert hashed != "SenhaForte123!"
    assert verify_password("SenhaForte123!", hashed)


def test_wrong_password_is_rejected():
    hashed = hash_password("SenhaForte123!")
    assert not verify_password("SenhaErrada999!", hashed)


def test_access_token_roundtrip():
    token = create_token(subject="user-123", token_type="access")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_tampered_token_is_rejected():
    token = create_token(subject="user-123", token_type="access")
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    with pytest.raises(jwt.PyJWTError):
        decode_token(tampered)


def test_totp_valid_code_is_accepted():
    import pyotp

    secret = generate_totp_secret()
    current_code = pyotp.TOTP(secret).now()
    assert verify_totp_code(secret, current_code)


def test_totp_invalid_code_is_rejected():
    secret = generate_totp_secret()
    assert not verify_totp_code(secret, "000000")

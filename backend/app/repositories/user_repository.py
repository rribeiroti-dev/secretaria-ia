"""
Repositório de usuários.

Toda query usa o client oficial do Supabase (que internamente já parametriza
os valores), evitando concatenação manual de SQL e, portanto, SQL injection.
"""
from typing import Any

from app.db.supabase_client import get_supabase_client

_TABLE = "app_users"


class UserRepository:
    def __init__(self):
        self._client = get_supabase_client()

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        result = (
            self._client.table(_TABLE)
            .select("*")
            .eq("email", email.lower().strip())
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        result = self._client.table(_TABLE).select("*").eq("id", user_id).limit(1).execute()
        return result.data[0] if result.data else None

    def create(self, email: str, full_name: str, password_hash: str, totp_secret_encrypted: str) -> dict[str, Any]:
        result = (
            self._client.table(_TABLE)
            .insert(
                {
                    "email": email.lower().strip(),
                    "full_name": full_name,
                    "password_hash": password_hash,
                    "totp_secret_encrypted": totp_secret_encrypted,
                    "totp_confirmed": False,
                    "failed_login_attempts": 0,
                }
            )
            .execute()
        )
        return result.data[0]

    def confirm_totp(self, user_id: str) -> None:
        self._client.table(_TABLE).update({"totp_confirmed": True}).eq("id", user_id).execute()

    def register_failed_login(self, user_id: str, attempts: int) -> None:
        self._client.table(_TABLE).update({"failed_login_attempts": attempts}).eq("id", user_id).execute()

    def reset_failed_login(self, user_id: str) -> None:
        self._client.table(_TABLE).update({"failed_login_attempts": 0}).eq("id", user_id).execute()

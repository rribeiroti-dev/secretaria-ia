"""
Repositório de memórias (documentos multimodais indexados por embedding).

Regra de segurança crítica: TODA leitura e escrita é filtrada por user_id.
Isso garante isolamento de dados entre usuários mesmo que a chave de service
role tenha acesso total ao banco — o isolamento é reforçado aqui na aplicação
e também via Row Level Security (RLS) no Postgres (ver database/schema.sql).
"""
from typing import Any

from app.db.supabase_client import get_supabase_client

_TABLE = "memories"


class MemoryRepository:
    def __init__(self):
        self._client = get_supabase_client()

    def create(
        self,
        user_id: str,
        source_type: str,
        extracted_text: str,
        embedding: list[float],
        original_filename: str | None = None,
    ) -> dict[str, Any]:
        result = (
            self._client.table(_TABLE)
            .insert(
                {
                    "user_id": user_id,
                    "source_type": source_type,
                    "extracted_text": extracted_text,
                    "original_filename": original_filename,
                    "embedding": embedding,
                }
            )
            .execute()
        )
        return result.data[0]

    def search_similar(self, user_id: str, query_embedding: list[float], top_k: int = 6) -> list[dict[str, Any]]:
        """
        Busca por similaridade vetorial usando a função RPC `match_memories`
        (definida em database/schema.sql), que já filtra por user_id dentro do SQL —
        assim um usuário nunca recebe memórias de outro, mesmo em caso de bug na API.
        """
        result = self._client.rpc(
            "match_memories",
            {
                "query_embedding": query_embedding,
                "match_user_id": user_id,
                "match_count": top_k,
            },
        ).execute()
        return result.data or []

    def list_all(self, user_id: str, limit: int = 100, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        result = (
            self._client.table(_TABLE)
            .select("*", count="exact")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or [], result.count or 0

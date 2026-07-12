"""
Cliente único do Supabase, usado com a chave de service role.

IMPORTANTE: a service key tem privilégios administrativos e NUNCA deve ser
exposta ao frontend. Ela vive apenas no backend, como variável de ambiente.
O frontend usa exclusivamente a API do nosso backend, nunca fala com o
Supabase diretamente.
"""
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)

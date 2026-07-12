"""
Rate limiting por IP (slowapi/limits).

Protege:
- Rotas de autenticação contra força bruta.
- Rotas de chat/mídia contra abuso das cotas gratuitas de API (Groq/OpenRouter).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

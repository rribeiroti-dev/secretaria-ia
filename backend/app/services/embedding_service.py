"""
Geração de embeddings para a memória vetorial (RAG).

Roda localmente no backend com sentence-transformers (modelo pequeno,
~80MB, CPU-friendly) para não depender de nenhuma API paga de embeddings.
O modelo é carregado uma única vez (singleton) e reaproveitado entre requests.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


@lru_cache
def _get_model() -> SentenceTransformer:
    settings = get_settings()
    return SentenceTransformer(settings.embedding_model_name)


def embed_text(text: str) -> list[float]:
    """Gera o vetor de embedding de um texto. Trunca textos muito longos por segurança/custo."""
    cleaned = text.strip()[:4000]
    model = _get_model()
    vector = model.encode(cleaned, normalize_embeddings=True)
    return vector.tolist()

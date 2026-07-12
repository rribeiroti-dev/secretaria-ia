"""
Geração de embeddings para a memória vetorial (RAG).

Roda localmente no backend com fastembed (ONNX Runtime — sem depender de
PyTorch), para caber confortavelmente no limite de RAM do free tier do
Render (512MB). O modelo escolhido é multilíngue (bom para português) e
gera vetores de 384 dimensões, compatível com o schema `vector(384)` do
banco. O modelo é carregado uma única vez (singleton) e reaproveitado
entre requests.
"""
from functools import lru_cache

from fastembed import TextEmbedding

from app.core.config import get_settings


@lru_cache
def _get_model() -> TextEmbedding:
    settings = get_settings()
    return TextEmbedding(model_name=settings.embedding_model_name)


def embed_text(text: str) -> list[float]:
    """Gera o vetor de embedding de um texto. Trunca textos muito longos por segurança/custo."""
    cleaned = text.strip()[:4000]
    model = _get_model()
    vector = next(model.embed([cleaned]))
    return vector.tolist()

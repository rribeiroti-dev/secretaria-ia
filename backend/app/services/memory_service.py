"""
Núcleo do agente: indexação de memórias e resposta ancorada (RAG).

Regra inegociável do produto: o agente SÓ PODE responder com base em algo que
o próprio usuário já inseriu. Isso é garantido em duas camadas:
  1. Camada de recuperação: se a busca vetorial não encontra nenhuma memória
     minimamente relevante, a API nem chama o LLM — devolve direto a
     mensagem padrão de "não há esse registro", sem chance de alucinação.
  2. Camada de geração: quando há memórias relevantes, o LLM recebe um
     system prompt que o instrui a responder apenas com base nesse contexto.
"""
from app.models.memory_schemas import MemoryItem, SourceType
from app.repositories.memory_repository import MemoryRepository
from app.services import llm_service
from app.services.embedding_service import embed_text

_NO_MEMORY_ANSWER = (
    "Não encontrei nenhum registro sobre isso no que você já me contou até agora. "
    "Se quiser, me envie essa informação (texto, áudio, foto ou vídeo) e eu guardo para consultas futuras."
)

# Memórias com similaridade abaixo deste limiar são descartadas do contexto,
# evitando que o LLM "force" uma resposta com base em algo pouco relacionado.
_MIN_SIMILARITY = 0.30

_SYSTEM_PROMPT_TEMPLATE = """Você é a secretária particular pessoal do usuário. Responda SEMPRE em português do Brasil.

Sua única fonte de verdade é o CONTEXTO abaixo, extraído de itens que o próprio usuário registrou anteriormente \
(textos, transcrições de áudio, descrições de fotos e de vídeos).

Regras obrigatórias:
- Use exclusivamente as informações do CONTEXTO para responder.
- Nunca use conhecimento geral ou externo ao CONTEXTO, mesmo que você "saiba" a resposta de outra forma.
- Se o CONTEXTO não contiver a resposta, diga claramente que não há esse registro na memória do usuário. Não invente.
- Seja objetiva, cordial e direta, no tom de uma secretária particular.

CONTEXTO:
{context}
"""


class MemoryService:
    def __init__(self):
        self._repository = MemoryRepository()

    def ingest_text(self, user_id: str, content: str) -> MemoryItem:
        return self._ingest(user_id, SourceType.TEXT, content, original_filename=None)

    def ingest_extracted_content(
        self, user_id: str, source_type: SourceType, extracted_text: str, filename: str | None
    ) -> MemoryItem:
        return self._ingest(user_id, source_type, extracted_text, original_filename=filename)

    def _ingest(self, user_id: str, source_type: SourceType, text: str, original_filename: str | None) -> MemoryItem:
        embedding = embed_text(text)
        record = self._repository.create(
            user_id=user_id,
            source_type=source_type.value,
            extracted_text=text,
            embedding=embedding,
            original_filename=original_filename,
        )
        return _to_memory_item(record)

    async def answer_question(self, user_id: str, question: str) -> tuple[str, list[MemoryItem], bool]:
        query_embedding = embed_text(question)
        raw_results = self._repository.search_similar(user_id, query_embedding, top_k=6)

        relevant = [r for r in raw_results if r.get("similarity", 0) >= _MIN_SIMILARITY]

        if not relevant:
            return _NO_MEMORY_ANSWER, [], False

        context_text = "\n---\n".join(
            f"[{r['source_type']} em {r['created_at']}]: {r['extracted_text']}" for r in relevant
        )
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(context=context_text)

        answer = await llm_service.generate_grounded_answer(system_prompt, question)
        used_memories = [_to_memory_item(r) for r in relevant]
        return answer, used_memories, True

    def list_history(self, user_id: str, limit: int, offset: int) -> tuple[list[MemoryItem], int]:
        records, total = self._repository.list_all(user_id, limit=limit, offset=offset)
        return [_to_memory_item(r) for r in records], total


def _to_memory_item(record: dict) -> MemoryItem:
    return MemoryItem(
        id=record["id"],
        source_type=SourceType(record["source_type"]),
        extracted_text=record["extracted_text"],
        original_filename=record.get("original_filename"),
        created_at=record["created_at"],
    )

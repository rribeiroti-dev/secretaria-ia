"""Schemas Pydantic de entrada/saída para ingestão de memória e chat."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    TEXT = "texto"
    AUDIO = "audio"
    IMAGE = "foto"
    VIDEO = "video"


class TextMemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MemoryItem(BaseModel):
    id: str
    source_type: SourceType
    extracted_text: str
    original_filename: str | None = None
    created_at: datetime


class MemoryIngestResponse(BaseModel):
    message: str
    memory: MemoryItem


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    used_memories: list[MemoryItem]
    grounded: bool  # False quando não havia contexto suficiente na memória do usuário


class HistoryResponse(BaseModel):
    items: list[MemoryItem]
    total: int

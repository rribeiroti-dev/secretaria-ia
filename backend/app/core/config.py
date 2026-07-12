"""
Configuração central da aplicação.

Todos os valores sensíveis (chaves de API, credenciais de banco, segredo JWT)
vêm exclusivamente de variáveis de ambiente. Nada aqui é hardcoded.
Em produção (Render), essas variáveis são definidas no painel do serviço.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Ambiente ---
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # --- Segurança / JWT ---
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # --- Criptografia de dados sensíveis em repouso (segredo TOTP) ---
    totp_encryption_key: str = Field(alias="TOTP_ENCRYPTION_KEY")

    # --- CORS ---
    # Lista de origens permitidas, separadas por vírgula (ex.: domínio do Netlify)
    allowed_origins_raw: str = Field(default="http://localhost:5500", alias="ALLOWED_ORIGINS")

    # --- Banco de dados / Auth (Supabase) ---
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_key: str = Field(alias="SUPABASE_SERVICE_KEY")

    # --- Provedores de IA ---
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")

    # Modelos (nomes configuráveis via env pois a oferta "free" muda com frequência)
    llm_chat_model: str = Field(default="meta-llama/llama-3.1-8b-instruct:free", alias="LLM_CHAT_MODEL")
    llm_vision_model: str = Field(default="meta-llama/llama-3.2-11b-vision-instruct:free", alias="LLM_VISION_MODEL")
    groq_whisper_model: str = Field(default="whisper-large-v3", alias="GROQ_WHISPER_MODEL")
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL_NAME")

    # --- Upload / limites (proteção contra abuso do free tier) ---
    max_upload_size_mb: int = Field(default=15, alias="MAX_UPLOAD_SIZE_MB")
    allowed_audio_types: str = Field(default="audio/webm,audio/mpeg,audio/wav,audio/ogg,audio/mp4", alias="ALLOWED_AUDIO_TYPES")
    allowed_image_types: str = Field(default="image/jpeg,image/png,image/webp", alias="ALLOWED_IMAGE_TYPES")
    allowed_video_types: str = Field(default="video/webm,video/mp4,video/quicktime", alias="ALLOWED_VIDEO_TYPES")

    # --- Rate limiting ---
    rate_limit_chat: str = Field(default="20/minute", alias="RATE_LIMIT_CHAT")
    rate_limit_media: str = Field(default="10/minute", alias="RATE_LIMIT_MEDIA")
    rate_limit_auth: str = Field(default="5/minute", alias="RATE_LIMIT_AUTH")

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cacheia a instância de configuração (lida do ambiente uma única vez)."""
    return Settings()

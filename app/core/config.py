from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    groq_api_key: str
    supabase_url: str
    supabase_key: str
    redis_url: str = "redis://localhost:6379"
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = ""
    evolution_instance: str = "cidadao-df"
    webhook_base_url: str = "http://localhost:8000"
    environment: str = "development"
    log_level: str = "INFO"

    # Modelos Groq — todos gratuitos
    model_fast: str = "llama-3.3-70b-versatile"      # chat principal
    model_vision: str = "llama-3.2-11b-vision-preview" # lê imagens
    model_whisper: str = "whisper-large-v3"            # transcreve áudio

    class Config:
        env_file = ".env"
        protected_namespaces = ('settings_',)

@lru_cache()
def get_settings() -> Settings:
    return Settings()

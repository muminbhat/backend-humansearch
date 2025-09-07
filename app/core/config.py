from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    environment: str = "dev"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    pdl_api_key: Optional[str] = None
    clearbit_api_key: Optional[str] = None
    redis_url: str = "redis://localhost:6379/0"
    replay_mode: bool = False

    class Config:
        env_file = ".env"


settings = Settings()


class Budget(BaseModel):
    max_wall_time_ms: int = 60000
    max_api_calls: int = 10
    max_llm_tokens: int = 20000


from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    environment: str = "dev"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    pdl_api_key: Optional[str] = None
    clearbit_api_key: Optional[str] = None
    redis_url: str = "redis://localhost:6379/0"
    replay_mode: bool = False
    use_redis_queue: bool = False
    # HTTP/cache/rate limiting/proxy
    http_cache_enabled: bool = True
    http_cache_dir: str = "backend/.cache"
    http_cache_ttl_s: int = 86400
    proxy_url: Optional[str] = None
    rate_limit_rps_pdl: float = 2.0
    rate_limit_rps_github: float = 2.0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


class Budget(BaseModel):
    max_wall_time_ms: int = 60000
    max_api_calls: int = 10
    max_llm_tokens: int = 20000


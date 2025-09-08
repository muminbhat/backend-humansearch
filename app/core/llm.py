from typing import List, Dict, Any, Optional
from openai import OpenAI
from .config import settings


def get_openai_client() -> Optional[OpenAI]:
    base = settings.openai_base_url
    # If neither base nor key is set, return None (LLM disabled)
    if not base and not settings.openai_api_key:
        return None
    return OpenAI(base_url=base, api_key=(settings.openai_api_key or "EMPTY"))


def build_json_schema_prompt(schema_hint: str, user_text: str) -> List[Dict[str, Any]]:
    system = (
        "You are a strict JSON generator. Respond ONLY with JSON matching the provided schema."
    )
    user = f"Schema:\n{schema_hint}\n\nUser Input:\n{user_text}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


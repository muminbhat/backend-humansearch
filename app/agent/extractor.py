from typing import Dict, Any
from pydantic import ValidationError
from ..schemas.search import NormalizedQuery, SearchInput
from ..utils.normalize import normalize_email, normalize_phone, normalize_name
from ..core.llm import get_openai_client, build_json_schema_prompt
from ..core.logging import logger
from ..core.config import settings
import re


async def extract_normalized_query(payload: SearchInput) -> NormalizedQuery:
	# First pass: deterministic utilities
	candidate = {
		"full_name": normalize_name(payload.name),
		"email": normalize_email(payload.email),
		"phone": normalize_phone(payload.phone),
		"username": payload.username.strip() if payload.username else None,
		"location": payload.location.strip() if payload.location else None,
		"context_text": payload.context_text.strip() if payload.context_text else None,
	}
	try:
		return NormalizedQuery(**candidate)
	except ValidationError:
		# Fallback: attempt a trivial correction (no real LLM yet)
		fallback = {
			**candidate,
		}
		return NormalizedQuery(**fallback)


async def extract_with_llm_fallback(payload: SearchInput) -> NormalizedQuery:
	"""Optional LLM-aided extraction using OpenAI-compatible API if configured."""
	client = get_openai_client()
	if client is None:
		# Regex fallback when LLM is not configured
		base = (await extract_normalized_query(payload)).model_dump()
		if payload.context_text and not base.get("full_name"):
			ctx_guess = extract_from_context_regex(payload.context_text)
			base.update({k: v for k, v in ctx_guess.items() if v})
			return NormalizedQuery(**base)
	# Build a minimal JSON schema hint
	schema_hint = (
		"{"
		"\"full_name\": string|null, \"email\": string|null, \"phone\": string|null, "
		"\"username\": string|null, \"location\": string|null, \"context_text\": string|null"
		"}"
	)
	messages = build_json_schema_prompt(schema_hint, payload.context_text or "")
	model_id = "meta-llama/Llama-3.2-3B-Instruct"
	import json
	last_err = None
	for _ in range(2):
		try:
			logger.info({"event": "llm_extractor_call", "model": model_id})
			resp = client.chat.completions.create(model=model_id, messages=messages, temperature=0)
			content = resp.choices[0].message.content or "{}"
			proposed = json.loads(content)
			# Merge with utility-normalized fields (utility has precedence for strict formatting)
			base = (await extract_normalized_query(payload)).model_dump()
			# If LLM didn't return fields, try regex from context
			if payload.context_text and not proposed.get("full_name"):
				proposed.update(extract_from_context_regex(payload.context_text))
			merged = {**proposed, **{k: v for k, v in base.items() if v is not None}}
			logger.info({"event": "llm_extractor_success"})
			return NormalizedQuery(**merged)
		except Exception as e:
			last_err = e
			logger.info({"event": "llm_extractor_retry", "error": str(e)})
			continue
	# On repeated failure, fall back to utilities + regex
	logger.info({"event": "llm_extractor_fallback"})
	base = (await extract_normalized_query(payload)).model_dump()
	if payload.context_text:
		base.update(extract_from_context_regex(payload.context_text))
	return NormalizedQuery(**base)


def extract_from_context_regex(context: str) -> Dict[str, Any]:
	"""Very lightweight regex-based extraction from free text."""
	result: Dict[str, Any] = {}
	if not context:
		return result
	# name: look for 'named <Name Words>' or 'person named <Name>' or '<Name> who'
	m = re.search(r"named\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", context, re.IGNORECASE)
	if not m:
		m = re.search(r"person\s+named\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", context, re.IGNORECASE)
	if not m:
		m = re.search(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b\s+who\b", context, re.IGNORECASE)
	if m:
		result["full_name"] = m.group(1).title()
	# location: look for 'in <Place>' or 'lives in <Place>'
	loc = re.search(r"\b(lives\s+in|in|from)\s+([A-Za-z][A-Za-z\s,&-]{2,})", context, re.IGNORECASE)
	if loc:
		result["location"] = loc.group(2).strip().title()
	return result

import hashlib
import json
import os
import time
from typing import Optional, Dict, Any
import httpx
from .config import settings
import asyncio


def _cache_key(method: str, url: str, params: Optional[Dict[str, Any]], headers: Optional[Dict[str, Any]]):
    raw = json.dumps({"m": method, "u": url, "p": params or {}, "h": headers or {}}, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def http_get(url: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None, timeout: float = 10.0, disable_cache: bool = False) -> httpx.Response:
    # Basic per-host rate limiting based on config
    host_tag = None
    rps = None
    if "peopledatalabs.com" in url:
        host_tag = "pdl"
        rps = settings.rate_limit_rps_pdl
    elif "api.github.com" in url:
        host_tag = "github"
        rps = settings.rate_limit_rps_github
    if host_tag and rps and rps > 0:
        await _respect_rate_limit(host_tag, rps)
    if settings.http_cache_enabled and not disable_cache:
        os.makedirs(settings.http_cache_dir, exist_ok=True)
        key = _cache_key("GET", url, params, headers)
        path = os.path.join(settings.http_cache_dir, key + ".json")
        if os.path.exists(path):
            if (time.time() - os.path.getmtime(path)) < settings.http_cache_ttl_s:
                with open(path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                r = httpx.Response(status_code=cached["status"], request=httpx.Request("GET", url), json=cached.get("json"))
                return r

    proxies = {"all": settings.proxy_url} if settings.proxy_url else None
    async with httpx.AsyncClient(timeout=timeout, proxies=proxies) as client:
        r = await client.get(url, params=params, headers=headers)

    if settings.http_cache_enabled and not disable_cache and r.status_code == 200:
        key = _cache_key("GET", url, params, headers)
        path = os.path.join(settings.http_cache_dir, key + ".json")
        try:
            payload = None
            try:
                payload = r.json()
            except Exception:
                payload = None
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"status": r.status_code, "json": payload}, f)
        except Exception:
            pass
    return r


# --- simple rate limiter ---
_LAST_CALL: Dict[str, float] = {}


async def _respect_rate_limit(tag: str, rps: float) -> None:
    min_interval = 1.0 / float(rps)
    now = time.monotonic()
    last = _LAST_CALL.get(tag)
    if last is not None:
        elapsed = now - last
        wait = min_interval - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
    _LAST_CALL[tag] = time.monotonic()


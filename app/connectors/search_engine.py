from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse
import asyncio
try:
    from ddgs import DDGS  # prefer new package
except Exception:
    from duckduckgo_search import DDGS
from ..schemas.search import NormalizedQuery
from ..schemas.profile import EvidenceItem, IdentityCandidate, Provenance
from ..schemas.common import SourceMethod


class DuckDuckGoConnector:
    name = "duckduckgo"

    async def fetch(self, query: NormalizedQuery) -> Dict[str, Any]:
        if not query.full_name and not query.location and not query.context_text:
            return {"evidences": [], "candidates": []}

        name = (query.full_name or "").strip()
        loc = (query.location or "").strip()
        name_phrase = f'"{name}"' if name else ""
        region_synonyms = {
            "kashmir": ["Kashmir", "Jammu and Kashmir", "J&K", "Srinagar", "Jammu"],
            "new york": ["New York", "NYC", "New York, NY"],
        }
        loc_variants = region_synonyms.get(loc.lower(), [loc] if loc else [])

        allow_domains = [
            "linkedin.com", "github.com", "twitter.com", "x.com", "instagram.com",
            "facebook.com", "crunchbase.com", "about.me", "medium.com", "angel.co",
        ]
        block_domains = [
            "support.microsoft.com", "yelp.com", "roofing", "stackoverflow.com",
        ]

        def domain_priority(d: str) -> int:
            for i, ad in enumerate(allow_domains):
                if ad in d:
                    return i
            return len(allow_domains) + 10

        def canonical_url(u: str) -> str:
            try:
                p = urlparse(u)
                clean = f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")
                return clean
            except Exception:
                return u

        # Tiered queries: strict (site-scoped), relaxed (general with loc), very relaxed (name only)
        queries: List[Tuple[str, str, str]] = []  # (tier, label, query)
        for site in ["linkedin.com/in", "twitter.com", "x.com", "github.com", "crunchbase.com", "facebook.com", "instagram.com"]:
            if name:
                if loc_variants:
                    for lv in loc_variants:
                        queries.append(("strict", site, f'{name_phrase} "{lv}" site:{site}'))
                else:
                    queries.append(("strict", site, f'{name_phrase} site:{site}'))
        if name:
            if loc_variants:
                for lv in loc_variants:
                    queries.append(("relaxed", "general", f'{name_phrase} "{lv}"'))
            else:
                queries.append(("relaxed", "general", f'{name_phrase}'))
        if name:
            queries.append(("very_relaxed", "general", f'{name_phrase}'))

        results: List[Dict[str, Any]] = []
        ddg_queries_run = 0

        async def run_query(q: str, label: str, max_results: int = 4, timeout_s: float = 2.5) -> List[Dict[str, Any]]:
            def _fetch() -> List[Dict[str, Any]]:
                out: List[Dict[str, Any]] = []
                with DDGS() as ddgs:
                    for r in ddgs.text(q, max_results=max_results):
                        out.append(r)
                return out
            try:
                res = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=timeout_s)
            except Exception:
                return []
            for r in res:
                r["_label"] = label
            return res

        # Global time budget ~7.5s
        total = 0
        for tier, label, q in queries[:10]:
            part = await run_query(q, label, max_results=4, timeout_s=2.5)
            results.extend(part)
            total += 1
            ddg_queries_run += 1
            if len(results) >= 24 or total >= 8:
                break

        name_tokens = [t.lower() for t in name.split() if t]
        loc_tokens = [lv.lower() for lv in loc_variants]

        def text_has_tokens(text: str, tokens: List[str]) -> bool:
            tl = (text or "").lower()
            return all(tok in tl for tok in tokens) if tokens else True

        def text_has_any(text: str, tokens: List[str]) -> bool:
            tl = (text or "").lower()
            return any(tok in tl for tok in tokens) if tokens else True

        filtered: Dict[str, Dict[str, Any]] = {}
        for r in results:
            url = r.get("href") or r.get("url")
            title = r.get("title") or r.get("heading") or ""
            snippet = r.get("body") or r.get("snippet") or ""
            if not url:
                continue
            host = urlparse(url).netloc.lower()
            if any(bd in host for bd in block_domains):
                continue
            # For strict passes require all tokens, otherwise any token
            # We infer pass strictness from URL label already embedded earlier is lost here; approximate by domain priority
            strict = domain_priority(host) <= 2  # linkedin/github/twitter treated as strict
            name_ok = (text_has_tokens(title, name_tokens) or text_has_tokens(snippet, name_tokens) or text_has_tokens(url, name_tokens)) if strict else (text_has_any(title, name_tokens) or text_has_any(snippet, name_tokens) or text_has_any(url, name_tokens))
            if name_tokens and not name_ok:
                continue
            loc_hit = any(lt in (title+" "+snippet+" "+url).lower() for lt in loc_tokens) if loc_tokens else True
            score = 0.2 + (0.4 if loc_hit else 0) + max(0, 0.6 - domain_priority(host) * 0.05)

            key = canonical_url(url)
            if key in filtered and filtered[key]["_score"] >= score:
                continue
            filtered[key] = {"url": key, "title": title, "snippet": snippet, "host": host, "_score": score}

        ranked = sorted(filtered.values(), key=lambda x: (-x["_score"]))[:5]

        prov = Provenance(source_name=self.name, method=SourceMethod.scrape, url=None)
        candidates: List[IdentityCandidate] = []
        evidences: List[EvidenceItem] = []
        for item in ranked:
            url = item["url"]
            title = item["title"]
            snippet = item["snippet"]
            cand = IdentityCandidate(
                display_name=name or title,
                usernames=[],
                locations=[loc] if loc else [],
                links=[url],
                score=float(item["_score"]),
                top_evidence=[EvidenceItem(field="link", value=url, confidence=0.6, provenance=prov, snippet=snippet)],
            )
            candidates.append(cand)
            evidences.append(EvidenceItem(field="search_result", value={"title": title, "url": url}, confidence=0.45, provenance=prov, snippet=snippet))

        # Expose simple stats for diagnostics
        self.last_stats = {"queries": ddg_queries_run, "hits": len(ranked)}
        return {"evidences": evidences, "candidates": candidates}


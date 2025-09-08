from typing import Dict, Any, List


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return lo


def judge_result(result: Dict[str, Any]) -> Dict[str, Any]:
    profile = result.get("profile", {})
    candidates: List[Dict[str, Any]] = result.get("candidates", [])

    # Normalize overall confidence by candidate scores
    if candidates:
        top = sorted(candidates, key=lambda c: c.get("score", 0), reverse=True)[0]
        profile["overall_confidence"] = _clamp(max(profile.get("overall_confidence", 0.0), top.get("score", 0.0)))
    else:
        profile["overall_confidence"] = _clamp(profile.get("overall_confidence", 0.0))

    # Drop obviously empty duplicates
    profile["emails"] = sorted(list({e for e in profile.get("emails", []) if e}))
    profile["usernames"] = sorted(list({u for u in profile.get("usernames", []) if u}))
    profile["locations"] = sorted(list({l for l in profile.get("locations", []) if l}))

    result["profile"] = profile
    return result


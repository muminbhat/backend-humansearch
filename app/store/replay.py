from typing import Dict, Any, Optional

_REPLAY_STORE: Dict[str, Any] = {}


def record(key: str, value: Any) -> None:
    _REPLAY_STORE[key] = value


def replay(key: str) -> Optional[Any]:
    return _REPLAY_STORE.get(key)


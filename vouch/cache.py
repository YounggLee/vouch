import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional


_CACHE_DIR = Path(os.environ.get("VOUCH_CACHE_DIR", "fixtures/responses"))


def _key(stage: str, payload: str) -> str:
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{stage}.{h}.json"


def load(stage: str, payload: str) -> Optional[Any]:
    path = _CACHE_DIR / _key(stage, payload)
    if path.exists():
        return json.loads(path.read_text())
    fallback = _CACHE_DIR / f"{stage}.json"
    if fallback.exists():
        return json.loads(fallback.read_text())
    return None


def save(stage: str, payload: str, result: Any) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _CACHE_DIR / _key(stage, payload)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

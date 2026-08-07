"""KIE API key pool — round-robin across primary + backup keys."""
from __future__ import annotations

import itertools
import threading
from typing import Iterator

from app.config import settings

_lock = threading.Lock()
_cycle: Iterator[str] | None = None


def _keys() -> list[str]:
    keys: list[str] = []
    for k in (settings.KIE_API_KEY, getattr(settings, "KIE_API_KEY_BACKUP", "")):
        k = (k or "").strip()
        if k and k not in keys:
            keys.append(k)
    return keys


def current_kie_api_key() -> str:
    """Return the next KIE key in round-robin order."""
    global _cycle
    keys = _keys()
    if not keys:
        return ""
    if len(keys) == 1:
        return keys[0]
    with _lock:
        if _cycle is None:
            _cycle = itertools.cycle(keys)
        return next(_cycle)


def kie_key_pool_status() -> dict:
    keys = _keys()
    return {
        "configured": len(keys),
        "pool_enabled": len(keys) > 1,
        # Never expose key material — only suffix for ops identification.
        "key_suffixes": [k[-4:] if len(k) >= 4 else "****" for k in keys],
    }

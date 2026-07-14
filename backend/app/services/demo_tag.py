"""Tag generation outputs with demo:true when running without provider keys."""
from __future__ import annotations

from typing import Any


def demo_mode_active() -> bool:
    try:
        from app.adapters.demo_provider import demo_mode_active as _active
        return bool(_active())
    except Exception:
        return True


def tag_result(item: dict[str, Any], *, demo: bool | None = None) -> dict[str, Any]:
    """Ensure a single result dict carries demo:true when appropriate."""
    out = dict(item)
    if demo is None:
        demo = demo_mode_active()
    if demo:
        out["demo"] = True
    return out


def tag_results(items: list[dict[str, Any]], *, demo: bool | None = None) -> list[dict[str, Any]]:
    return [tag_result(i, demo=demo) for i in items]

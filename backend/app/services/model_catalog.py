"""
Model catalog governance — verified live SKUs vs gateway-mapped labs.

Promotion rules (honest):
  active  = live-gateway verified (manual test or smoke+admin promote)
  mapped  = has a concrete KIE model ID (not a guess), may still 422
  lab     = unverified guess — never default-routed
"""
from __future__ import annotations

# Confirmed in kie_adapter KIE_MODEL_IDS "verified working" / "verified-recognised"
# sections — safe to mark active in catalog once smoke mapping check passes.
GATEWAY_VERIFIED_IDS: frozenset[str] = frozenset({
    "gpt-image-2",
    "nano-banana",
    "nano-banana-pro",
    "imagen-4",
    "seedance-2.0",
    "seedance-2.0-fast",
    "kling-2.5-turbo",
    "kling-2.1-pro",
    "kling-2.1-master",
})

# Explicit unverified guesses in kie_adapter — must stay beta until live test.
GATEWAY_GUESS_IDS: frozenset[str] = frozenset({
    "flux-1.1-pro",
    "flux-1-dev",
    "flux-kontext",
    "ideogram-v3",
    "recraft-v3",
    "seedream-3",
    "qwen-image",
    "hidream-i1",
    "sdxl",
    "midjourney-v7",
    "grok-image",
    "sora-2",
    "sora-2-pro",
    "runway-gen4",
    "runway-gen3",
    "luma-ray-2",
    "pika-2.2",
    "hunyuan-video",
    "ltx-video",
    "grok-video",
})


def catalog_integrity() -> dict:
    """Report active/mapped/guess alignment for ops dashboards."""
    from app.api.models_info import MODELS
    from app.adapters.kie_adapter import KIE_MODEL_IDS

    active = [m.id for m in MODELS if m.status == "active"]
    beta = [m.id for m in MODELS if m.status == "beta"]
    missing_map = [m.id for m in MODELS if m.id not in KIE_MODEL_IDS]
    active_not_verified = [i for i in active if i not in GATEWAY_VERIFIED_IDS]
    verified_not_active = [i for i in GATEWAY_VERIFIED_IDS if i not in active and any(m.id == i for m in MODELS)]
    return {
        "total": len(MODELS),
        "active_count": len(active),
        "beta_count": len(beta),
        "active_ids": active,
        "missing_kie_map": missing_map,
        "active_outside_verified_set": active_not_verified,
        "verified_not_yet_active": verified_not_active,
        "guess_ids_in_catalog": [i for i in GATEWAY_GUESS_IDS if any(m.id == i for m in MODELS)],
    }


def should_be_active(model_id: str) -> bool:
    return model_id in GATEWAY_VERIFIED_IDS

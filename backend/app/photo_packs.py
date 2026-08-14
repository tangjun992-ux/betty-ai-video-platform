"""Photo Pack registry — batch SKU pipelines (对标 Yapper Product Shots / Headshots / Photo Packs).

Each pack expands one input (a subject description and/or a reference image) into
a BATCH of professional, distinct variations (angles / scenes / styles) that are
generated in one job. i2i packs keep the uploaded product/person; t2i packs
generate from the subject text.
"""
from __future__ import annotations

from typing import Any

# Each variation: (label, styling prompt fragment)
PHOTO_PACKS: dict[str, dict[str, Any]] = {
    "product": {
        "label": "电商产品图",
        "category": "product",
        "desc": "一张产品图 → 白底 / 角度 / 细节 / 场景 多图套系",
        "model": "gpt-image-2",
        "i2i": True,   # accepts a product reference image (kept intact)
        "aspect": "1:1",
        "variations": [
            {"label": "白底正面", "prompt": "centered front view on a pure white seamless background, professional softbox studio lighting, razor-sharp product focus, subtle floor reflection, e-commerce catalog quality"},
            {"label": "45° 角", "prompt": "three-quarter 45-degree hero angle on clean white background, premium studio lighting, crisp shadows, commercial catalog shot"},
            {"label": "俯拍细节", "prompt": "top-down flat-lay macro detail shot, even diffused lighting, crisp texture and material detail, minimal props"},
            {"label": "生活场景", "prompt": "lifestyle scene on a marble surface with soft natural daylight, tasteful props and shallow depth of field, editorial commercial mood"},
            {"label": "纯色背景", "prompt": "studio shot on a soft pastel color-block backdrop, gradient light, bold minimal advertising composition"},
            {"label": "水花动感", "prompt": "dynamic splash / floating composition with motion energy, dramatic rim light, high-end advertising key visual"},
        ],
    },
    "headshots": {
        "label": "职业头像",
        "category": "portrait",
        "desc": "一张自拍 → 商务 / LinkedIn / 证件 / 创意 专业头像套系",
        "model": "nano-banana-pro",
        "i2i": True,   # accepts a selfie (identity kept)
        "aspect": "1:1",
        "variations": [
            {"label": "商务正装", "prompt": "corporate executive headshot, dark tailored suit, neutral studio backdrop, soft beauty-dish key light, confident approachable expression, sharp eyes"},
            {"label": "LinkedIn", "prompt": "LinkedIn profile headshot, smart business-casual, bright modern office background with gentle bokeh, natural window light, warm friendly smile"},
            {"label": "证件照", "prompt": "formal ID / passport style headshot, plain light-grey background, perfectly front-facing, neutral expression, flat even lighting, no shadows"},
            {"label": "创意肖像", "prompt": "editorial creative portrait, moody directional side light, dark seamless background, cinematic color grade, magazine cover quality"},
        ],
    },
    "lifestyle": {
        "label": "生活方式包",
        "category": "portrait",
        "desc": "自然光生活场景社媒套系",
        "model": "imagen-4",
        "i2i": False,
        "aspect": "4:3",
        "variations": [
            {"label": "晨光居家", "prompt": "cozy morning at home, soft window daylight, warm minimal interior, candid lifestyle moment, film-like color grade"},
            {"label": "咖啡馆", "prompt": "aesthetic cafe scene, natural light, latte and notebook, shallow depth of field, social-media lifestyle shot"},
            {"label": "城市街拍", "prompt": "urban street style, golden hour backlight, candid walking motion, editorial fashion lifestyle"},
            {"label": "自然户外", "prompt": "outdoor nature lifestyle, soft overcast light, greenery bokeh, relaxed authentic mood"},
        ],
    },
    "brand": {
        "label": "品牌视觉包",
        "category": "product",
        "desc": "极简品牌海报与几何视觉套系",
        "model": "gpt-image-2",
        "i2i": False,
        "aspect": "1:1",
        "variations": [
            {"label": "极简海报", "prompt": "minimal brand poster, generous negative space, premium typography placement area, soft gradient background"},
            {"label": "几何构图", "prompt": "bold geometric brand composition, primary color blocks, clean vector shapes, modern advertising layout"},
            {"label": "渐变质感", "prompt": "smooth premium gradient background, subtle grain, soft studio light, abstract brand key visual"},
            {"label": "产品排版", "prompt": "product-forward brand layout with clean grid, high-contrast lighting, marketing hero banner space"},
        ],
    },
}


def resolve_pack_model(pack: dict[str, Any], override: str | None = None) -> str:
    """Prefer the pack SKU only when it is verified-active; else cheapest active image model."""
    from app.api.models_info import default_verified_model, is_verified

    for candidate in (override, pack.get("model"), "nano-banana", "gpt-image-2"):
        cid = (candidate or "").strip()
        if cid and is_verified(cid):
            return cid
    return default_verified_model("image") or "nano-banana"


def pack_cost_per(model: str) -> int:
    from app.api.models_info import MODELS

    info = next((m for m in MODELS if m.id == model), None)
    if info and info.capabilities.cost_per_image_credits:
        return int(info.capabilities.cost_per_image_credits)
    return 2


def quote_pack(pack: dict[str, Any], *, pack_id: str, count: int | None, model: str | None = None) -> dict[str, Any]:
    variations = pack["variations"]
    n = len(variations) if not count else max(1, min(int(count), len(variations)))
    resolved = resolve_pack_model(pack, model)
    per = pack_cost_per(resolved)
    preferred = pack.get("model") or resolved
    return {
        "pack_id": pack_id,
        "pack_label": pack["label"],
        "count": n,
        "cost_per": per,
        "estimated_cost_credits": per * n,
        "preferred_model": preferred,
        "resolved_model": resolved,
        "model_fallback": resolved != preferred,
        "honesty": "N 个独立图像任务（非单请求多图）。模型仅用已验证 active；不足则 402，不会中途扣一半。",
    }


def list_packs() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pid, p in PHOTO_PACKS.items():
        q = quote_pack(p, pack_id=pid, count=len(p["variations"]))
        out.append({
            "id": pid,
            "label": p["label"],
            "category": p["category"],
            "desc": p["desc"],
            "i2i": p["i2i"],
            "aspect": p.get("aspect", "1:1"),
            "variation_count": len(p["variations"]),
            "variations": [{"label": v["label"]} for v in p["variations"]],
            "model": q["resolved_model"],
            "preferred_model": q["preferred_model"],
            "cost_per": q["cost_per"],
            "honesty": q["honesty"],
        })
    return out


def get_pack(pack_id: str) -> dict[str, Any] | None:
    return PHOTO_PACKS.get((pack_id or "").strip())


def build_variation_prompt(pack: dict[str, Any], variation: dict[str, Any], subject: str, has_ref: bool) -> str:
    """Compose the final prompt for one pack variation.

    i2i (reference image present): styling instruction + identity/shape lock.
    t2i: subject description + styling.
    """
    styling = variation["prompt"]
    subj = (subject or "").strip()
    if has_ref and pack.get("i2i"):
        keep = (
            "Keep the original subject's identity, shape, colors and branding exactly unchanged."
            if pack["category"] == "product"
            else "Keep the person's facial identity and features exactly the same."
        )
        base = f"{styling}. {keep}"
        return f"{subj}。{base}" if subj else base
    # t2i needs the subject in the prompt
    if subj:
        return f"{subj}，{styling}"
    return styling

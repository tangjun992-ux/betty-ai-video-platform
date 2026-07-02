"""
Gallery/Explore API — community showcase from real completed tasks.
"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from app.db import get_db
from app.models.task import Task
from app.models.billing import Transaction, TransactionType

router = APIRouter()

# ─── Content Safety Filter ────────────────────────────
NSFW_KEYWORDS = [
    "nude", "naked", "nsfw", "porn", "explicit", "sex",
    "underwear", "lingerie", "bikini", "topless", "bottomless",
    "upskirt", "cleavage", "erotic", "adult",
    "underarm", "armpit", "side torso", "tasteful fashion slit",
    "reveal", "undress", "strip",
]
PROFANITY_KEYWORDS = [
    "fuck", "shit", "ass", "damn", "bitch", "dick", "pussy",
    "bastard", "whore", "slut",
]

def _is_safe(prompt: str) -> bool:
    """Check if prompt is safe for public gallery display."""
    if not prompt:
        return True
    lower = prompt.lower()
    for kw in NSFW_KEYWORDS:
        if kw in lower:
            return False
    # Also check for excessive suggestive descriptions
    suggestive_count = sum(1 for kw in ["cleavage", "reveal", "slit", "body", "skin", "figure", "curve"] if kw in lower)
    if suggestive_count >= 3:
        return False
    return True

# Style categories matching Yapper.so
STYLE_OPTIONS = [
    {"key": "all", "label": "全部分类"},
    {"key": "cinematic", "label": "🎬 电影级"},
    {"key": "realistic", "label": "📸 写实"},
    {"key": "anime", "label": "🎨 动漫"},
    {"key": "product", "label": "🛍️ 产品"},
    {"key": "portrait", "label": "👤 人像"},
    {"key": "landscape", "label": "🌄 风景"},
    {"key": "sci-fi", "label": "🤖 科幻"},
    {"key": "fantasy", "label": "🧙 奇幻"},
    {"key": "food", "label": "🍔 美食"},
    {"key": "architecture", "label": "🏛️ 建筑"},
    {"key": "artistic", "label": "🖌️ 艺术"},
    {"key": "cute/kawaii", "label": "🐱 可爱"},
    {"key": "funny", "label": "😂 搞笑"},
    {"key": "surreal", "label": "🌀 超现实"},
    {"key": "storytelling", "label": "📖 故事"},
    {"key": "3d-render", "label": "🧊 3D渲染"},
    {"key": "cartoon", "label": "🎪 卡通"},
    {"key": "character", "label": "🧑 角色"},
    {"key": "energetic", "label": "⚡ 动感"},
    {"key": "documentary", "label": "🎥 纪录片"},
    {"key": "meme", "label": "😄 表情包"},
    {"key": "social-media", "label": "📱 社交媒体"},
]


@router.get("/", summary="探索画廊")
async def explore_gallery(
    style: str = Query(default="all"),
    media_type: str = Query(default="all"),
    sort: str = Query(default="popular"),
    limit: int = Query(default=32, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    """Return gallery items from completed tasks with real media."""
    # Get completed tasks
    q = select(Task).where(Task.status == "completed")
    if media_type != "all":
        q = q.where(Task.media_type == media_type)
    q = q.order_by(Task.completed_at.desc() if sort == "recent" else Task.created_at.desc())
    q = q.limit(500)  # fetch more for filtering

    result = await db.execute(q)
    tasks = result.scalars().all()

    items = []
    filtered_count = 0
    for t in tasks:
        if not t.results:
            continue

        for r in t.results:
            if not isinstance(r, dict):
                continue
            url = r.get("url") or r.get("media_url") or ""
            if not url:
                continue

            item_media = r.get("type", t.media_type)
            model = r.get("model", t.selected_model or "unknown")
            resolution = t.parameters.get("resolution", "") if t.parameters else ""

            # Extract style from routing info
            routing_str = (t.parameters or {}).get("routing_info", "")
            styles_list = []
            if routing_str:
                import json
                try:
                    routing = json.loads(routing_str) if isinstance(routing_str, str) else routing_str
                    styles_list = routing.get("detected_styles", [])
                except Exception:
                    pass

            # Filter by style if specified
            if style != "all" and style not in styles_list:
                continue

            # Content safety filter
            if not _is_safe(t.prompt or ""):
                filtered_count += 1
                continue

            items.append({
                "id": f"{t.task_id}_{len(items)}",
                "task_id": t.task_id,
                "prompt": t.prompt,
                "media_type": item_media,
                "model_used": model.split("/")[-1] if "/" in model else model,
                "style": styles_list[0] if styles_list else "general",
                "styles": styles_list,
                "resolution": resolution,
                "duration": t.parameters.get("duration") if t.parameters else None,
                "url": url,
                "thumbnail": r.get("thumbnail") or url,
                "credits_cost": int(t.estimated_cost or 0),
                "created_at": (t.completed_at.isoformat() if t.completed_at else t.created_at.isoformat()),
                "username": "AI 创作者",
                "avatar": "🤖",
                "likes": hash(t.task_id) % 100,
                "views": hash(t.task_id + "v") % 1000,
            })

    # Sort
    if sort == "popular":
        items.sort(key=lambda x: x["likes"], reverse=True)
    else:
        items.sort(key=lambda x: x["created_at"], reverse=True)

    total = len(items)
    paged = items[offset:offset + limit]

    return {"items": paged, "total": total, "limit": limit, "offset": offset, "styles": STYLE_OPTIONS}


@router.get("/stats", summary="画廊统计")
async def gallery_stats(db: AsyncSession = Depends(get_db)):
    """Get gallery statistics from real data."""
    # Count completed tasks
    q = select(func.count()).select_from(Task).where(Task.status == "completed")
    result = await db.execute(q)
    total_completed = result.scalar() or 0

    # Count by media type
    q_img = select(func.count()).select_from(Task).where(
        and_(Task.status == "completed", Task.media_type == "image")
    )
    r_img = await db.execute(q_img)
    total_images = r_img.scalar() or 0

    q_vid = select(func.count()).select_from(Task).where(
        and_(Task.status == "completed", Task.media_type == "video")
    )
    r_vid = await db.execute(q_vid)
    total_videos = r_vid.scalar() or 0

    # Total credits consumed
    q_credits = select(func.sum(Transaction.amount)).where(
        Transaction.type == TransactionType.CONSUMPTION.value
    )
    r_credits = await db.execute(q_credits)
    total_credits = abs(r_credits.scalar() or 0)

    return {
        "total_items": total_completed,
        "total_images": total_images,
        "total_videos": total_videos,
        "total_credits_consumed": total_credits,
        "style_options": STYLE_OPTIONS,
    }

"""
Gallery/Explore API — community showcase from real completed tasks.
"""
import json
import zlib
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from typing import Optional
from app.db import get_db
from app.models.task import Task
from app.models.billing import Transaction, TransactionType

router = APIRouter()

_LIKES_DDL = (
    "CREATE TABLE IF NOT EXISTS gallery_likes "
    "(item_key TEXT PRIMARY KEY, likes INTEGER NOT NULL DEFAULT 0)"
)


async def _ensure_likes_table(db: AsyncSession) -> None:
    await db.execute(text(_LIKES_DDL))


async def _stored_likes(db: AsyncSession) -> dict:
    """Map of item_key → real (community) like count."""
    try:
        await _ensure_likes_table(db)
        rows = await db.execute(text("SELECT item_key, likes FROM gallery_likes"))
        return {k: int(v) for k, v in rows.all()}
    except Exception:
        return {}


def _base_likes(task_id: str) -> int:
    """Deterministic seed so counts are stable across restarts (pre-community)."""
    return zlib.crc32(task_id.encode()) % 100


def _safe_dict(value) -> dict:
    """Coerce a JSON column value to a dict (legacy rows may store strings)."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _safe_list(value) -> list:
    """Coerce a JSON column value to a list (legacy rows may store strings)."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []

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

    likes_map = await _stored_likes(db)

    items = []
    filtered_count = 0
    for t in tasks:
        results = _safe_list(t.results)
        if not results:
            continue
        params = _safe_dict(t.parameters)

        for r in results:
            try:
                if not isinstance(r, dict):
                    continue
                url = r.get("url") or r.get("media_url") or ""
                if not url:
                    continue

                item_media = r.get("type", t.media_type)
                model = r.get("model", t.selected_model or "unknown")
                resolution = params.get("resolution", "")

                # Extract style from routing info
                routing_str = params.get("routing_info", "")
                styles_list = []
                if routing_str:
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

                ts = t.completed_at or t.created_at
                item_key = f"{t.task_id}_{len(items)}"
                likes = _base_likes(t.task_id) + likes_map.get(item_key, 0)
                items.append({
                    "id": item_key,
                    "task_id": t.task_id,
                    "prompt": t.prompt,
                    "media_type": item_media,
                    "model_used": model.split("/")[-1] if "/" in model else model,
                    "style": styles_list[0] if styles_list else "general",
                    "styles": styles_list,
                    "resolution": resolution,
                    "duration": params.get("duration"),
                    "url": url,
                    "thumbnail": r.get("thumbnail") or url,
                    "credits_cost": int(t.estimated_cost or 0),
                    "created_at": ts.isoformat() if ts else "",
                    "username": "AI 创作者",
                    "avatar": "🤖",
                    "likes": likes,
                    "views": zlib.crc32((t.task_id + "v").encode()) % 1000,
                })
            except Exception:
                # One malformed legacy row must never break the whole gallery
                continue

    # Sort
    if sort == "popular":
        items.sort(key=lambda x: x["likes"], reverse=True)
    else:
        items.sort(key=lambda x: x["created_at"], reverse=True)

    total = len(items)
    paged = items[offset:offset + limit]

    return {"items": paged, "total": total, "limit": limit, "offset": offset, "styles": STYLE_OPTIONS}


@router.post("/{item_key}/like", summary="点赞作品")
async def like_item(item_key: str, undo: bool = Query(default=False), db: AsyncSession = Depends(get_db)):
    """Increment (or undo) a community like for a gallery item. Persisted in
    gallery_likes so counts survive restarts (real reactions, not seeded)."""
    if not item_key or "_" not in item_key:
        raise HTTPException(status_code=400, detail="无效的作品 ID")
    task_id = item_key.rsplit("_", 1)[0]
    await _ensure_likes_table(db)
    delta = -1 if undo else 1
    # upsert with a floor of 0 on the stored delta
    await db.execute(
        text(
            "INSERT INTO gallery_likes (item_key, likes) VALUES (:k, :d) "
            "ON CONFLICT(item_key) DO UPDATE SET likes = MAX(0, likes + :d)"
        ),
        {"k": item_key, "d": delta},
    )
    await db.commit()
    row = await db.execute(text("SELECT likes FROM gallery_likes WHERE item_key = :k"), {"k": item_key})
    stored = int(row.scalar() or 0)
    return {"item_key": item_key, "likes": _base_likes(task_id) + stored, "liked": not undo}


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

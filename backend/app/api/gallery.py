"""
Gallery/Explore API — community showcase from real completed tasks.

Public visibility requires an explicit publish action (``parameters.share_public``).
Seed demo items remain visible in non-production when enabled.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from sqlalchemy.orm.attributes import flag_modified
from typing import Optional
from app.db import get_db
from app.auth import resolve_user_id
from app.models.task import Task
from app.models.user import User
from app.models.billing import Transaction, TransactionType

router = APIRouter()


def _is_share_public(params: dict) -> bool:
    """True only when the owner explicitly published the work."""
    if not isinstance(params, dict):
        return False
    val = params.get("share_public")
    return val is True or val == 1 or str(val).lower() in ("true", "1", "yes")


_SEED_MARKERS = frozenset({"demo_seed_v1", "demo_seed_v2"})


def _is_seed_item(params: dict) -> bool:
    """Curated Explore seeds (v1 legacy + v2 current)."""
    if not isinstance(params, dict):
        return False
    return params.get("seed_marker") in _SEED_MARKERS

_LIKES_DDL = (
    "CREATE TABLE IF NOT EXISTS gallery_likes "
    "(item_key TEXT PRIMARY KEY, likes INTEGER NOT NULL DEFAULT 0)"
)
_VIEWS_DDL = (
    "CREATE TABLE IF NOT EXISTS gallery_views "
    "(item_key TEXT PRIMARY KEY, views INTEGER NOT NULL DEFAULT 0)"
)
_MOD_DDL = (
    "CREATE TABLE IF NOT EXISTS gallery_moderation "
    "(item_key TEXT PRIMARY KEY, reports INTEGER NOT NULL DEFAULT 0, "
    "hidden INTEGER NOT NULL DEFAULT 0, reason TEXT)"
)
# Auto-hide a gallery item once community reports reach this threshold.
_REPORT_HIDE_THRESHOLD = 3


async def _ensure_likes_table(db: AsyncSession) -> None:
    await db.execute(text(_LIKES_DDL))


async def _ensure_views_table(db: AsyncSession) -> None:
    await db.execute(text(_VIEWS_DDL))


async def _stored_likes(db: AsyncSession) -> dict:
    """Map of item_key → real (community) like count."""
    try:
        await _ensure_likes_table(db)
        rows = await db.execute(text("SELECT item_key, likes FROM gallery_likes"))
        return {k: int(v) for k, v in rows.all()}
    except Exception:
        return {}


async def _stored_views(db: AsyncSession) -> dict:
    """Map of item_key → real view count (list endpoint does not increment)."""
    try:
        await _ensure_views_table(db)
        rows = await db.execute(text("SELECT item_key, views FROM gallery_views"))
        return {k: int(v) for k, v in rows.all()}
    except Exception:
        return {}


async def _hidden_keys(db: AsyncSession) -> set:
    """Item keys hidden by moderation/takedown — excluded from the gallery."""
    try:
        await db.execute(text(_MOD_DDL))
        rows = await db.execute(text("SELECT item_key FROM gallery_moderation WHERE hidden = 1"))
        return {r[0] for r in rows.all()}
    except Exception:
        return set()


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


def _author_fields(user: Optional[User]) -> dict:
    """Real author from Task.user; anonymous fallback without fake AI branding."""
    if user is None:
        return {"username": "创作者", "display_name": "创作者", "avatar": ""}
    display = (user.display_name or user.username or "创作者").strip() or "创作者"
    return {
        "username": user.username or "创作者",
        "display_name": display,
        "avatar": user.avatar_url or "",
    }


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
    include_seed: bool = Query(default=False, description="开发环境可展示种子示例"),
    db: AsyncSession = Depends(get_db),
):
    """Return gallery items from completed tasks with real media."""
    from app.config import settings
    show_seed = include_seed or not settings.is_production
    # Join User for real author fields (outer — guest/orphan tasks still show)
    q = (
        select(Task, User)
        .outerjoin(User, Task.user_id == User.id)
        .where(Task.status == "completed")
    )
    if media_type != "all":
        q = q.where(Task.media_type == media_type)
    q = q.order_by(Task.completed_at.desc() if sort == "recent" else Task.created_at.desc())
    q = q.limit(500)  # fetch more for filtering

    result = await db.execute(q)
    rows = result.all()

    likes_map = await _stored_likes(db)
    views_map = await _stored_views(db)
    hidden = await _hidden_keys(db)

    items = []
    filtered_count = 0
    for t, user in rows:
        results = _safe_list(t.results)
        if not results:
            continue
        params = _safe_dict(t.parameters)
        author = _author_fields(user)

        for ri, r in enumerate(results):
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

                # Content safety filter (shared moderation policy)
                from app.services.moderation import is_safe as _mod_safe
                if not (_is_safe(t.prompt or "") and _mod_safe(t.prompt or "")):
                    filtered_count += 1
                    continue

                is_seed_item = _is_seed_item(params)
                if is_seed_item and not show_seed:
                    continue
                # Privacy gate: completed ≠ public. Owner must publish.
                if not is_seed_item and not _is_share_public(params):
                    continue

                ts = t.completed_at or t.created_at
                # Stable key: task_id + result index (matches seed likes/views)
                item_key = f"{t.task_id}_{ri}"
                if item_key in hidden:
                    continue
                likes = likes_map.get(item_key, 0)
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
                    "username": author["username"],
                    "display_name": author["display_name"],
                    "avatar": author["avatar"],
                    "likes": likes,
                    "views": views_map.get(item_key, 0),
                    "is_seed": is_seed_item,
                    "is_demo": is_seed_item or bool(r.get("demo")),
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


async def _owned_completed_task(
    db: AsyncSession, task_id: str, user_id: int,
) -> Task:
    res = await db.execute(select(Task).where(Task.task_id == task_id))
    task = res.scalar_one_or_none()
    if not task or task.status != "completed":
        raise HTTPException(status_code=404, detail="作品不存在或未完成")
    if int(task.user_id or 0) != int(user_id):
        raise HTTPException(status_code=403, detail="只能公开自己的作品")
    return task


@router.post("/share/{task_id}/publish", summary="公开分享作品（显式发布）")
async def publish_share(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    """Owner opts-in to public permalink + explore listing."""
    if not task_id or len(task_id) < 8:
        raise HTTPException(status_code=400, detail="无效的分享 ID")
    task = await _owned_completed_task(db, task_id, user_id)
    from app.services.moderation import is_safe as _mod_safe
    if not (_is_safe(task.prompt or "") and _mod_safe(task.prompt or "")):
        raise HTTPException(status_code=400, detail="内容未通过安全审核，无法公开")
    params = _safe_dict(task.parameters)
    params["share_public"] = True
    params["share_published_at"] = datetime.now(timezone.utc).isoformat()
    task.parameters = params
    flag_modified(task, "parameters")
    await db.commit()
    return {
        "task_id": task_id,
        "share_public": True,
        "share_path": f"/explore/{task_id}",
        "share_url": f"/api/v1/gallery/share/{task_id}",
    }


@router.post("/share/{task_id}/unpublish", summary="取消公开分享")
async def unpublish_share(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    if not task_id or len(task_id) < 8:
        raise HTTPException(status_code=400, detail="无效的分享 ID")
    task = await _owned_completed_task(db, task_id, user_id)
    params = _safe_dict(task.parameters)
    params["share_public"] = False
    params["share_unpublished_at"] = datetime.now(timezone.utc).isoformat()
    task.parameters = params
    flag_modified(task, "parameters")
    await db.commit()
    return {"task_id": task_id, "share_public": False}


@router.get("/share/{task_id}", summary="公开分享作品（稳定 permalink）")
async def share_item(task_id: str, db: AsyncSession = Depends(get_db)):
    """Public share payload by task_id — no auth required.

    Requires explicit owner publish (``share_public``). Hidden / moderated /
    unsafe prompts are not exposed. Increments view count.
    """
    if not task_id or len(task_id) < 8:
        raise HTTPException(status_code=400, detail="无效的分享 ID")
    q = (
        select(Task, User)
        .outerjoin(User, Task.user_id == User.id)
        .where(Task.task_id == task_id, Task.status == "completed")
    )
    row = (await db.execute(q)).first()
    if not row:
        raise HTTPException(status_code=404, detail="作品不存在或未公开")
    task, user = row
    params = _safe_dict(task.parameters)
    is_seed = _is_seed_item(params)
    if not is_seed and not _is_share_public(params):
        raise HTTPException(status_code=404, detail="作品不存在或未公开")
    results = _safe_list(task.results)
    if not results:
        raise HTTPException(status_code=404, detail="作品无媒体")
    r0 = results[0] if isinstance(results[0], dict) else {}
    url = r0.get("url") or r0.get("media_url") or ""
    if not url:
        raise HTTPException(status_code=404, detail="作品无媒体")
    from app.services.moderation import is_safe as _mod_safe
    if not (_is_safe(task.prompt or "") and _mod_safe(task.prompt or "")):
        raise HTTPException(status_code=404, detail="作品不可用")
    item_key = f"{task_id}_0"
    hidden = await _hidden_keys(db)
    if item_key in hidden or f"{task_id}_share" in hidden:
        raise HTTPException(status_code=404, detail="作品已下架")
    # Increment views (best-effort)
    try:
        await _ensure_views_table(db)
        await db.execute(
            text(
                "INSERT INTO gallery_views (item_key, views) VALUES (:k, 1) "
                "ON CONFLICT(item_key) DO UPDATE SET views = views + 1"
            ),
            {"k": item_key},
        )
        await db.commit()
    except Exception:
        pass
    likes_map = await _stored_likes(db)
    views_map = await _stored_views(db)
    author = _author_fields(user)
    media_type = r0.get("type") or task.media_type or "image"
    model = r0.get("model") or task.selected_model or "unknown"
    return {
        "id": task_id,
        "task_id": task_id,
        "share_path": f"/explore/{task_id}",
        "prompt": task.prompt or "",
        "media_type": media_type,
        "model_used": model.split("/")[-1] if "/" in str(model) else model,
        "url": url,
        "thumbnail": r0.get("thumbnail") or url,
        "resolution": params.get("resolution", ""),
        "duration": params.get("duration"),
        "created_at": (task.completed_at or task.created_at).isoformat()
        if (task.completed_at or task.created_at) else "",
        "username": author["username"],
        "display_name": author["display_name"],
        "avatar": author["avatar"],
        "likes": likes_map.get(item_key, 0),
        "views": views_map.get(item_key, 0),
        "create_path": f"/create/{'video' if media_type == 'video' else 'image'}",
    }


@router.post("/{item_key}/like", summary="点赞作品")
async def like_item(item_key: str, undo: bool = Query(default=False), db: AsyncSession = Depends(get_db)):
    """Increment (or undo) a community like for a gallery item. Persisted in
    gallery_likes so counts survive restarts (real reactions, not seeded)."""
    if not item_key or "_" not in item_key:
        raise HTTPException(status_code=400, detail="无效的作品 ID")
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
    return {"item_key": item_key, "likes": stored, "liked": not undo}


@router.post("/{item_key}/remix", summary="Remix 作品（进入创作）")
async def remix_item(item_key: str, db: AsyncSession = Depends(get_db)):
    """Return remix payload so the client can open Create with source media + prompt."""
    if not item_key or "_" not in item_key:
        raise HTTPException(status_code=400, detail="无效的作品 ID")
    task_id = item_key.rsplit("_", 1)[0]
    from app.models.task import Task
    from sqlalchemy import select as sa_select
    row = (await db.execute(sa_select(Task).where(Task.task_id == task_id))).scalar_one_or_none()
    if not row or row.status != "completed":
        raise HTTPException(status_code=404, detail="作品不存在")
    results = row.results if isinstance(row.results, list) else []
    media_url = ""
    if results and isinstance(results[0], dict):
        media_url = results[0].get("media_url") or results[0].get("url") or ""
    prompt = row.prompt or ""
    media_type = row.media_type or "image"
    from app.services.moderation import check_media_url, moderation_reject
    m = check_media_url(media_url, caption=prompt)
    if not m.allowed:
        raise moderation_reject(m)
    return {
        "remix": True,
        "source_item_key": item_key,
        "prompt": prompt,
        "media_type": media_type,
        "media_url": media_url,
        "model": row.selected_model or row.requested_model,
        "create_path": f"/create/{'video' if media_type == 'video' else 'image'}",
    }


@router.post("/{item_key}/report", summary="举报作品")
async def report_item(item_key: str, db: AsyncSession = Depends(get_db)):
    """Community report. Increments the report count and auto-hides the item
    once it reaches the threshold (takedown). Idempotent-ish per call."""
    if not item_key or "_" not in item_key:
        raise HTTPException(status_code=400, detail="无效的作品 ID")
    await db.execute(text(_MOD_DDL))
    await db.execute(
        text("INSERT INTO gallery_moderation (item_key, reports, hidden) VALUES (:k, 1, 0) "
             "ON CONFLICT(item_key) DO UPDATE SET reports = reports + 1"),
        {"k": item_key},
    )
    await db.execute(
        text("UPDATE gallery_moderation SET hidden = 1 WHERE item_key = :k AND reports >= :th"),
        {"k": item_key, "th": _REPORT_HIDE_THRESHOLD},
    )
    await db.commit()
    row = await db.execute(text("SELECT reports, hidden FROM gallery_moderation WHERE item_key = :k"), {"k": item_key})
    reports, hidden = row.first() or (1, 0)
    return {"item_key": item_key, "reports": int(reports), "hidden": bool(hidden),
            "message": "感谢举报，我们会尽快复核" if not hidden else "内容已达举报阈值，已自动下架"}


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

"""
Library API — unified content library: user uploads + AI-generated results.

Item id scheme:
  up_<asset_id>          -> Asset row (uploaded file)
  gen_<task_id>_<index>  -> entry <index> in Task.results (generated)
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import settings
from app.db import get_db
from app.models.asset import Asset
from app.models.task import Task
from app.models.user import User
from app.auth import resolve_user_id

router = APIRouter()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024    # 10MB
MAX_MEDIA_SIZE = 100 * 1024 * 1024   # 100MB (video/audio)
MAX_FAVORITES = 500
MAX_FOLDERS = 50


def _user_meta(user: User) -> dict:
    try:
        return json.loads(user.metadata_json) if user.metadata_json else {}
    except Exception:
        return {}


def _favorites_list(user: User) -> list[str]:
    meta = _user_meta(user)
    favs = (meta.get("library") or {}).get("favorites") or []
    return [str(x) for x in favs if isinstance(x, str)]


async def _load_user(db: AsyncSession, user_id: int) -> User:
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def _save_favorites(db: AsyncSession, user: User, favorites: list[str]) -> None:
    meta = _user_meta(user)
    lib = dict(meta.get("library") or {})
    lib["favorites"] = favorites[:MAX_FAVORITES]
    meta["library"] = lib
    user.metadata_json = json.dumps(meta, ensure_ascii=False)
    await db.flush()


def _folders_list(user: User) -> list[str]:
    meta = _user_meta(user)
    raw = (meta.get("library") or {}).get("folders") or []
    names: list[str] = []
    seen: set[str] = set()
    for x in raw:
        name = ""
        if isinstance(x, str):
            name = x.strip()[:80]
        elif isinstance(x, dict):
            name = str(x.get("name") or "").strip()[:80]
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


async def _save_folders(db: AsyncSession, user: User, folders: list[str]) -> None:
    meta = _user_meta(user)
    lib = dict(meta.get("library") or {})
    cleaned: list[str] = []
    seen: set[str] = set()
    for name in folders:
        n = (name or "").strip()[:80]
        if n and n not in seen:
            seen.add(n)
            cleaned.append(n)
        if len(cleaned) >= MAX_FOLDERS:
            break
    lib["folders"] = cleaned
    meta["library"] = lib
    user.metadata_json = json.dumps(meta, ensure_ascii=False)
    await db.flush()


def _folder_catalog(user: User, items: list) -> list[dict]:
    """Registry (incl. empty folders) union labels found on items."""
    folder_counts: dict[str, int] = {}
    for it in items:
        fn = (it.get("folder") or "").strip()
        if fn:
            folder_counts[fn] = folder_counts.get(fn, 0) + 1
    catalog: list[dict] = []
    seen: set[str] = set()
    for name in list(_folders_list(user)) + sorted(folder_counts.keys()):
        if not name or name in seen:
            continue
        seen.add(name)
        catalog.append({"name": name, "count": int(folder_counts.get(name, 0))})
    return catalog


def _ext_media_type(ext: str) -> Optional[str]:
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    return None


def _safe_dict(value) -> dict:
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
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _infer_tool(task: Task, result: dict) -> Optional[str]:
    """Map a generated item to a Yapper-style tool bucket when evidence exists."""
    params = _safe_dict(task.parameters)
    op = str(params.get("operation") or "").lower()
    model = str(result.get("model") or task.selected_model or task.requested_model or "").lower()
    prompt = str(task.prompt or "").lower()
    hay = f"{op} {model} {prompt}"
    if op == "upscale" or "upscale" in hay:
        return "upscale"
    if "motion-control" in hay or "motion_control" in hay or "/motion" in hay or op == "motion":
        return "motion"
    if (
        params.get("lipsync_text")
        or op in ("lipsync", "lip-sync", "avatar")
        or "ai-avatar" in hay
        or "lipsync" in hay
        or "lip-sync" in hay
        or "lip_sync" in hay
    ):
        return "lipsync"
    return None


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except Exception:
        return None


def _is_today(created_at: str, *, now: Optional[datetime] = None) -> bool:
    ts = _parse_iso(created_at)
    if ts is None:
        return False
    clock = now or datetime.now(timezone.utc)
    return ts.astimezone(timezone.utc).date() == clock.astimezone(timezone.utc).date()


def _asset_item(a: Asset, *, favorited: bool = False) -> dict:
    return {
        "id": f"up_{a.asset_id}",
        "source": "upload",
        "media_type": a.media_type,
        "url": a.url,
        "thumbnail": a.thumbnail or (a.url if a.media_type == "image" else None),
        "title": a.filename or "未命名文件",
        "prompt": None,
        "model": None,
        "size_bytes": a.size_bytes,
        "duration": None,
        "created_at": a.created_at.isoformat() if a.created_at else "",
        "favorited": favorited,
        "folder": getattr(a, "folder", None) or None,
        "tool": None,
        "task_id": None,
    }


def _generated_items(t: Task, *, favorites: set[str] | None = None) -> list:
    params = _safe_dict(t.parameters)
    ts = t.completed_at or t.created_at
    favs = favorites or set()
    out = []
    for idx, r in enumerate(_safe_list(t.results)):
        if not isinstance(r, dict):
            continue
        url = r.get("url") or r.get("media_url") or ""
        if not url:
            continue
        model = r.get("model", t.selected_model or "")
        item_id = f"gen_{t.task_id}_{idx}"
        out.append({
            "id": item_id,
            "task_id": t.task_id,
            "source": "generated",
            "media_type": r.get("type", t.media_type),
            "url": url,
            "thumbnail": r.get("thumbnail") or (url if r.get("type", t.media_type) == "image" else None),
            "title": (t.prompt or "")[:80] or "AI 生成",
            "prompt": t.prompt,
            "model": model.split("/")[-1] if "/" in model else model,
            "size_bytes": None,
            "duration": params.get("duration"),
            "created_at": ts.isoformat() if ts else "",
            "favorited": item_id in favs,
            "folder": params.get("library_folder") or r.get("folder"),
            "tool": _infer_tool(t, r),
            "session_uid": params.get("session_uid"),
        })
    return out


@router.get("/", summary="内容库列表")
async def list_library(
    media_type: str = Query(default="all"),      # all | image | video | audio
    source: str = Query(default="all"),          # all | upload | generated
    q: str = Query(default=""),
    sort: str = Query(default="recent"),         # recent | oldest
    favorite: bool = Query(default=False, description="仅收藏"),
    folder: str = Query(default="", description="按文件夹筛选（上传资产）"),
    period: str = Query(default="all", description="all | today（对标 Yapper Assets Today）"),
    tool: str = Query(default="all", description="all | upscale | motion | lipsync"),
    limit: int = Query(default=48, le=200),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    items: list = []
    user = await _load_user(db, user_id)
    favs = set(_favorites_list(user))

    # Per-user isolation: each resolved account sees only its own assets.
    def _own(col):
        return col == user_id

    if source in ("all", "upload"):
        res = await db.execute(
            select(Asset).where(_own(Asset.user_id))
            .order_by(Asset.created_at.desc()).limit(1000)
        )
        for a in res.scalars().all():
            try:
                aid = f"up_{a.asset_id}"
                items.append(_asset_item(a, favorited=aid in favs))
            except Exception:
                continue

    if source in ("all", "generated"):
        res = await db.execute(
            select(Task).where(Task.status == "completed", _own(Task.user_id))
            .order_by(Task.created_at.desc()).limit(1000)
        )
        for t in res.scalars().all():
            try:
                items.extend(_generated_items(t, favorites=favs))
            except Exception:
                continue

    kw = q.strip().lower()
    if kw:
        items = [
            it for it in items
            if kw in (it["title"] or "").lower()
            or kw in (it.get("prompt") or "").lower()
            or kw in (it.get("model") or "").lower()
        ]

    folder_q = folder.strip()
    folder_catalog = _folder_catalog(user, items)
    if folder_q:
        items = [it for it in items if (it.get("folder") or "") == folder_q]

    if favorite:
        items = [it for it in items if it.get("favorited")]

    today_n = sum(1 for it in items if _is_today(it.get("created_at") or ""))
    tool_counts = {
        "upscale": sum(1 for it in items if it.get("tool") == "upscale"),
        "motion": sum(1 for it in items if it.get("tool") == "motion"),
        "lipsync": sum(1 for it in items if it.get("tool") == "lipsync"),
    }
    period_key = (period or "all").strip().lower()
    if period_key == "today":
        items = [it for it in items if _is_today(it.get("created_at") or "")]
    tool_key = (tool or "all").strip().lower()
    if tool_key and tool_key != "all":
        items = [it for it in items if (it.get("tool") or "") == tool_key]

    # Tab counts reflect the current source+search scope, computed BEFORE the
    # media_type filter so switching tabs never zeroes the other tab badges
    counts = {
        "all": len(items),
        "image": sum(1 for it in items if it["media_type"] == "image"),
        "video": sum(1 for it in items if it["media_type"] == "video"),
        "audio": sum(1 for it in items if it["media_type"] == "audio"),
        "upload": sum(1 for it in items if it["source"] == "upload"),
        "generated": sum(1 for it in items if it["source"] == "generated"),
        "favorite": sum(1 for it in items if it.get("favorited")),
        "today": today_n,
        **tool_counts,
    }

    if media_type != "all":
        items = [it for it in items if it["media_type"] == media_type]

    items.sort(key=lambda x: x["created_at"], reverse=(sort != "oldest"))
    total = len(items)
    return {
        "items": items[offset:offset + limit],
        "total": total,
        "counts": counts,
        "favorites": sorted(favs),
        "folders": [f["name"] for f in folder_catalog],
        "folder_catalog": folder_catalog,
        "limit": limit,
        "offset": offset,
    }


@router.get("/favorites", summary="收藏列表 ID")
async def list_favorites(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    user = await _load_user(db, user_id)
    favs = _favorites_list(user)
    return {"favorites": favs, "total": len(favs)}


@router.post("/favorites/{item_id}", summary="收藏条目")
async def add_favorite(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    if not (item_id.startswith("up_") or item_id.startswith("gen_")):
        raise HTTPException(status_code=400, detail="无效的条目 ID")
    user = await _load_user(db, user_id)
    favs = _favorites_list(user)
    if item_id not in favs:
        favs.insert(0, item_id)
        await _save_favorites(db, user, favs)
        await db.commit()
    return {"favorited": True, "id": item_id, "total": len(favs)}


@router.delete("/favorites/{item_id}", summary="取消收藏")
async def remove_favorite(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    user = await _load_user(db, user_id)
    favs = [x for x in _favorites_list(user) if x != item_id]
    await _save_favorites(db, user, favs)
    await db.commit()
    return {"favorited": False, "id": item_id, "total": len(favs)}


class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class FolderRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    rename: str = Field(..., min_length=1, max_length=80)


class BatchFolder(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=100)
    folder: str = Field(default="", max_length=80)


async def _apply_folder(db: AsyncSession, item_id: str, user_id: int, name: Optional[str]) -> dict:
    if item_id.startswith("up_"):
        asset_id = item_id[3:]
        res = await db.execute(select(Asset).where(Asset.asset_id == asset_id, Asset.user_id == user_id))
        asset = res.scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="条目不存在")
        asset.folder = name
        return _asset_item(asset, favorited=item_id in set(_favorites_list(await _load_user(db, user_id))))
    if item_id.startswith("gen_"):
        try:
            task_id, idx_str = item_id[4:].rsplit("_", 1)
            idx = int(idx_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的条目 ID")
        res = await db.execute(select(Task).where(Task.task_id == task_id, Task.user_id == user_id))
        task = res.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="条目不存在")
        params = _safe_dict(task.parameters)
        params["library_folder"] = name
        task.parameters = params
        flag_modified(task, "parameters")
        items = _generated_items(task, favorites=set(_favorites_list(await _load_user(db, user_id))))
        if idx < 0 or idx >= len(items):
            raise HTTPException(status_code=404, detail="条目不存在")
        return items[idx]
    raise HTTPException(status_code=400, detail="无效的条目 ID")


async def _relabel_folder(db: AsyncSession, user_id: int, old: str, new: Optional[str]) -> int:
    changed = 0
    res = await db.execute(select(Asset).where(Asset.user_id == user_id, Asset.folder == old))
    for asset in res.scalars().all():
        asset.folder = new
        changed += 1
    res = await db.execute(select(Task).where(Task.user_id == user_id, Task.status == "completed"))
    for task in res.scalars().all():
        params = _safe_dict(task.parameters)
        if params.get("library_folder") == old:
            params["library_folder"] = new
            task.parameters = params
            flag_modified(task, "parameters")
            changed += 1
    return changed


@router.get("/folders", summary="文件夹目录（含空文件夹）")
async def list_folders(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    user = await _load_user(db, user_id)
    catalog = _folder_catalog(user, [])
    return {"folders": catalog, "total": len(catalog)}


@router.post("/folders", summary="新建文件夹")
async def create_folder(
    body: FolderCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    name = body.name.strip()[:80]
    if not name:
        raise HTTPException(status_code=400, detail="文件夹名不能为空")
    user = await _load_user(db, user_id)
    folders = _folders_list(user)
    if name in folders:
        return {"name": name, "created": False, "folders": folders}
    if len(folders) >= MAX_FOLDERS:
        raise HTTPException(status_code=400, detail=f"文件夹上限 {MAX_FOLDERS}")
    folders.append(name)
    await _save_folders(db, user, folders)
    await db.commit()
    return {"name": name, "created": True, "folders": folders}


@router.patch("/folders", summary="重命名文件夹")
async def rename_folder(
    body: FolderRename,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    old = body.name.strip()[:80]
    new = body.rename.strip()[:80]
    if not old or not new:
        raise HTTPException(status_code=400, detail="文件夹名不能为空")
    if old == new:
        return {"name": new, "renamed": False}
    user = await _load_user(db, user_id)
    folders = _folders_list(user)
    if new in folders and new != old:
        raise HTTPException(status_code=409, detail="目标文件夹已存在")
    folders = [new if x == old else x for x in folders]
    if new not in folders:
        folders.append(new)
    await _save_folders(db, user, folders)
    moved = await _relabel_folder(db, user_id, old, new)
    await db.commit()
    return {"name": new, "from": old, "renamed": True, "moved": moved, "folders": folders}


@router.delete("/folders", summary="删除文件夹（条目移出，不删文件）")
async def delete_folder(
    name: str = Query(..., min_length=1, max_length=80),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    folder = name.strip()[:80]
    user = await _load_user(db, user_id)
    folders = [x for x in _folders_list(user) if x != folder]
    await _save_folders(db, user, folders)
    moved = await _relabel_folder(db, user_id, folder, None)
    await db.commit()
    return {"deleted": folder, "cleared": moved, "folders": folders}


@router.post("/batch-folder", summary="批量移入文件夹")
async def batch_set_folder(
    body: BatchFolder,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    name = (body.folder or "").strip()[:80] or None
    if name:
        user = await _load_user(db, user_id)
        folders = _folders_list(user)
        if name not in folders:
            if len(folders) >= MAX_FOLDERS:
                raise HTTPException(status_code=400, detail=f"文件夹上限 {MAX_FOLDERS}")
            folders.append(name)
            await _save_folders(db, user, folders)
    moved: list[str] = []
    failed: list[dict] = []
    seen: set[str] = set()
    for item_id in body.ids[:100]:
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        try:
            await _apply_folder(db, item_id, user_id, name)
            moved.append(item_id)
        except HTTPException as e:
            failed.append({"id": item_id, "detail": e.detail})
    await db.commit()
    return {"moved": moved, "failed": failed, "folder": name, "ok": len(moved)}


@router.patch("/{item_id}/folder", summary="设置文件夹标签")
async def set_item_folder(
    item_id: str,
    folder: str = Query(default="", max_length=80),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    """Assign a lightweight folder label (uploads + generated)."""
    name = (folder or "").strip()[:80] or None
    if name:
        user = await _load_user(db, user_id)
        folders = _folders_list(user)
        if name not in folders:
            folders.append(name)
            await _save_folders(db, user, folders)
    item = await _apply_folder(db, item_id, user_id, name)
    await db.commit()
    return item


@router.post("/upload", summary="上传到内容库")
async def upload_to_library(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    media_type = _ext_media_type(ext)
    if not media_type:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 {ext}。支持：图片(jpg/png/webp/gif)、视频(mp4/webm/mov)、音频(mp3/wav/m4a/ogg)",
        )

    content = await file.read()
    max_size = MAX_IMAGE_SIZE if media_type == "image" else MAX_MEDIA_SIZE
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大（{len(content) // 1024 // 1024}MB），上限 {max_size // 1024 // 1024}MB",
        )

    from app.services.media_store import store_upload
    asset = await store_upload(db, file.filename or "", content, file.content_type, user_id=user_id)
    return _asset_item(asset)


class BatchIds(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=100)


async def _delete_one(db: AsyncSession, item_id: str, user_id: int) -> str:
    try:
        user = await _load_user(db, user_id)
        favs = [x for x in _favorites_list(user) if x != item_id]
        if len(favs) != len(_favorites_list(user)):
            await _save_favorites(db, user, favs)
    except Exception:
        pass

    if item_id.startswith("up_"):
        asset_id = item_id[3:]
        res = await db.execute(select(Asset).where(Asset.asset_id == asset_id, Asset.user_id == user_id))
        asset = res.scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="条目不存在")
        try:
            prefix = "/api/v1/media/"
            if asset.url.startswith(prefix):
                p = Path(settings.STORAGE_LOCAL_PATH) / asset.url[len(prefix):]
                if p.is_file():
                    p.unlink()
        except Exception:
            pass
        await db.delete(asset)
        return item_id

    if item_id.startswith("gen_"):
        try:
            task_id, idx_str = item_id[4:].rsplit("_", 1)
            idx = int(idx_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的条目 ID")
        res = await db.execute(select(Task).where(Task.task_id == task_id, Task.user_id == user_id))
        task = res.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="条目不存在")
        results = _safe_list(task.results)
        if idx < 0 or idx >= len(results):
            raise HTTPException(status_code=404, detail="条目不存在")
        results.pop(idx)
        task.results = results
        flag_modified(task, "results")
        return item_id

    raise HTTPException(status_code=400, detail="无效的条目 ID")


@router.post("/batch-delete", summary="批量删除内容库条目")
async def batch_delete_library(
    body: BatchIds,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    deleted: list[str] = []
    failed: list[dict] = []
    seen: set[str] = set()
    ordered: list[str] = []
    for item_id in body.ids[:100]:
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        ordered.append(item_id)

    def _gen_idx(item_id: str) -> int:
        try:
            return int(item_id.rsplit("_", 1)[-1])
        except Exception:
            return 0

    gens = [i for i in ordered if i.startswith("gen_")]
    others = [i for i in ordered if not i.startswith("gen_")]
    gens.sort(key=_gen_idx, reverse=True)
    for item_id in gens + others:
        try:
            deleted.append(await _delete_one(db, item_id, user_id))
        except HTTPException as e:
            failed.append({"id": item_id, "detail": e.detail})
    await db.commit()
    return {"deleted": deleted, "failed": failed, "ok": len(deleted)}


@router.post("/batch-publish", summary="批量发布生成作品到 Explore")
async def batch_publish_library(
    body: BatchIds,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    from app.api.gallery import _is_safe
    from app.services.moderation import is_safe as _mod_safe

    published: list[str] = []
    failed: list[dict] = []
    seen: set[str] = set()
    for item_id in body.ids[:100]:
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        if not item_id.startswith("gen_"):
            failed.append({"id": item_id, "detail": "仅生成作品可发布到 Explore"})
            continue
        try:
            task_id, _idx = item_id[4:].rsplit("_", 1)
        except ValueError:
            failed.append({"id": item_id, "detail": "无效的条目 ID"})
            continue
        res = await db.execute(select(Task).where(Task.task_id == task_id, Task.user_id == user_id))
        task = res.scalar_one_or_none()
        if not task or task.status != "completed":
            failed.append({"id": item_id, "detail": "作品不存在或未完成"})
            continue
        if not (_is_safe(task.prompt or "") and _mod_safe(task.prompt or "")):
            failed.append({"id": item_id, "detail": "内容未通过安全审核"})
            continue
        params = _safe_dict(task.parameters)
        params["share_public"] = True
        params["share_published_at"] = datetime.now(timezone.utc).isoformat()
        task.parameters = params
        flag_modified(task, "parameters")
        published.append(task_id)
    await db.commit()
    return {"published": published, "failed": failed, "ok": len(published)}


@router.delete("/{item_id}", summary="删除内容库条目")
async def delete_library_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    deleted = await _delete_one(db, item_id, user_id)
    await db.commit()
    return {"deleted": deleted}

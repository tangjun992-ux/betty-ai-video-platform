"""
Image generation Celery tasks — calls real adapters with smart fallback.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone

from celery_app import app
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.media_store import persist_results
from app.services.model_health import model_health, validate_generation_results

logger = logging.getLogger(__name__)


def _get_db_url_sync():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if db_url.startswith("sqlite+aiosqlite"):
        db_url = db_url.replace("sqlite+aiosqlite", "sqlite")
    elif db_url.startswith("postgresql+asyncpg"):
        db_url = db_url.replace("postgresql+asyncpg", "postgresql")
    return db_url


from app.tasks.task_db import update_task as _update_task


def _load_adapters():
    """Lazy load adapters with error handling."""
    from app.adapters.registry import get_adapter, _load_all_adapters
    _load_all_adapters()
    return get_adapter


def _run_async(coro):
    """Run async code in sync Celery context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _size_to_aspect(size: str) -> str:
    """Map pixel resolution (e.g. 1920x1080) to the aspect string edit APIs expect."""
    m = {
        "1080x1080": "1:1", "1024x1024": "1:1",
        "1920x1080": "16:9", "1280x720": "16:9",
        "1080x1920": "9:16", "720x1280": "9:16",
        "1280x960": "4:3",
        "1536x1024": "3:2",
    }
    return m.get((size or "").strip(), "auto")


def _parse_size(size: str) -> tuple[int, int] | None:
    try:
        w, h = str(size).lower().strip().split("x")
        w, h = int(w), int(h)
        return (w, h) if w > 0 and h > 0 else None
    except Exception:
        return None


def _enforce_resolution(output: list[dict], size: str) -> list[dict]:
    """Strictly enforce the requested output resolution.

    Some providers ignore the requested aspect/size and always return a fixed
    canvas (e.g. 1024x1024). To guarantee the delivered image matches the
    user's parameters we center-crop + resize the persisted file to (w,h).
    """
    wh = _parse_size(size)
    if not wh:
        return output
    w, h = wh
    try:
        from PIL import Image
    except Exception:
        logger.warning("image_tasks: PIL unavailable, skip resolution enforcement")
        return output
    from app.adapters.demo_provider import _local_media_path

    for out in output:
        if out.get("type") != "image":
            continue
        url = out.get("url") or ""
        p = _local_media_path(url)
        if not p or not os.path.exists(p):
            continue
        try:
            with Image.open(p) as im:
                im = im.convert("RGB")
                iw, ih = im.size
                if (iw, ih) == (w, h):
                    out["resolution"] = f"{w}x{h}"
                    continue
                scale = max(w / iw, h / ih)
                nw, nh = max(w, int(iw * scale + 0.5)), max(h, int(ih * scale + 0.5))
                im2 = im.resize((nw, nh), Image.LANCZOS)
                left = max(0, (nw - w) // 2)
                top = max(0, (nh - h) // 2)
                im2 = im2.crop((left, top, left + w, top + h))
                im2.save(p)
            out["resolution"] = f"{w}x{h}"
        except Exception as e:  # noqa: BLE001
            logger.warning("image_tasks: enforce resolution failed for %s: %s", url[:80], e)
    return output


def _to_public_ref(url: str) -> str:
    """Ensure a reference image URL is publicly fetchable by KIE.

    User uploads and locally generated media live at /api/v1/media/... which is
    only reachable inside our network. For real i2i/edit the provider must fetch
    the image, so we re-upload local/localhost URLs via KIE's file API and use
    the returned public URL. Already-public URLs are returned unchanged.
    """
    if not url or not isinstance(url, str):
        return url
    u = url.strip()
    if not u:
        return u
    if (u.startswith("http://") or u.startswith("https://")) and (
        "/api/v1/media" not in u and "localhost" not in u and "127.0.0.1" not in u
    ):
        return u
    try:
        from app.adapters.demo_provider import _local_media_path
        from app.adapters.kie_adapter import KieAdapter
        import uuid as _uuid

        p = _local_media_path(u)
        if not p or not os.path.exists(p):
            logger.warning("image_tasks: cannot localize ref image %s", u[:100])
            return u
        with open(p, "rb") as f:
            data = f.read()
        ext = os.path.splitext(p)[1].lstrip(".").lower() or "png"
        ct = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
        return _run_async(
            KieAdapter().upload_public_url(
                data, filename=f"ref_{_uuid.uuid4().hex[:8]}.{ext}", content_type=ct
            )
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("image_tasks: public-ize ref failed for %s: %s", u[:100], e)
        return u


def _broadcast_progress(task_id: str, progress: int, stage: str, message: str = "", preview_url: str = ""):
    """Send real-time progress update via WebSocket (non-blocking, fire-and-forget)."""
    try:
        from app.api.websocket import broadcast_task_progress

        async def _send():
            payload = {
                "type": "progress",
                "progress": progress,
                "current_stage": stage,
                "message": message or stage,
            }
            if preview_url:
                payload["preview_url"] = preview_url
            await broadcast_task_progress(task_id, payload)

        _run_async(_send())
    except Exception:
        pass  # WebSocket broadcast is best-effort, don't fail the task


@app.task(
    bind=True,
    name="app.tasks.image_tasks.generate_image",
    queue="image_q",
    max_retries=2,
    acks_late=True,
)
def generate_image_task(
    self, db_task_id: str, model: str, prompt: str, params: dict
) -> dict:
    """Image generation with automatic fallback."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_dir not in os.getcwd():
        os.chdir(backend_dir)

    self.update_state(state="PROGRESS", meta={"current_stage": "routing", "progress": 10})
    _update_task(
        db_task_id, status="generating", selected_model=model,
        progress=10, current_stage="routing",
        started_at=datetime.now(timezone.utc),
    )
    _broadcast_progress(db_task_id, 10, "routing", "正在分析提示词并选择最优模型...")

    self.update_state(state="PROGRESS", meta={"current_stage": "generating", "progress": 30})
    _update_task(db_task_id, progress=30, current_stage="generating")
    _broadcast_progress(db_task_id, 30, "generating", "模型已选定，开始生成...")

    # Demo mode: render locally when no provider key is configured.
    from app.adapters.demo_provider import demo_mode_active, DemoAdapter
    if demo_mode_active():
        adapter = DemoAdapter(model_label=model)
    else:
        # Get adapter and fallback config
        get_adapter = _load_adapters()
        adapter = get_adapter(model)
        if not adapter:
            # Try fallback
            from app.fallback_handler import get_fallback
            fallback_id = get_fallback(model)
            if fallback_id:
                adapter = get_adapter(fallback_id)
                model = fallback_id
                _update_task(db_task_id, selected_model=model, current_stage="fallback_used")

        if not adapter:
            return _mark_failed(db_task_id, f"No adapter for model or fallback: {model}")

    size = params.get("size", params.get("resolution", "1024x1024"))
    style = params.get("style", "auto")
    count = params.get("count", 1)
    seed = params.get("seed")
    # True i2i: multi-ref list or legacy single image_url
    ref_images = [
        u for u in (params.get("reference_images") or [])
        if isinstance(u, str) and u.strip()
    ][:4]
    if not ref_images and params.get("image_url"):
        ref_images = [str(params["image_url"]).strip()]

    self.update_state(state="PROGRESS", meta={"current_stage": "generating", "progress": 50})
    _update_task(db_task_id, progress=50)
    stage_msg = "参考图编辑中..." if ref_images else "模型正在创作中，请稍候..."
    _broadcast_progress(db_task_id, 50, "generating", stage_msg)

    # Real i2i/edit: reference images must be publicly fetchable by the provider.
    if ref_images:
        from app.adapters.demo_provider import demo_mode_active as _demo_active
        if not _demo_active():
            ref_images = [_to_public_ref(u) for u in ref_images]

    started = time.monotonic()
    try:
        if ref_images:
            edit_fn = getattr(adapter, "edit_image", None)
            if callable(edit_fn):
                result = _run_async(
                    edit_fn(
                        image_urls=ref_images,
                        prompt=prompt,
                        image_size=_size_to_aspect(size),
                    )
                )
            else:
                result = _run_async(
                    adapter.generate_image(
                        prompt=prompt, model_id=model, size=size, style=style,
                        count=count, seed=seed, image_url=ref_images[0],
                        image_urls=ref_images,
                    )
                )
        else:
            result = _run_async(
                adapter.generate_image(
                    prompt=prompt, model_id=model, size=size, style=style,
                    count=count, seed=seed,
                )
            )
        # Adapt single GenerationResult to list for uniform processing
        results = [result] if not isinstance(result, list) else result
        quality_ok, quality_error = validate_generation_results(results, "image")
        if not quality_ok:
            raise RuntimeError(quality_error)

        self.update_state(state="PROGRESS", meta={"current_stage": "uploading", "progress": 80})
        _update_task(db_task_id, progress=80, current_stage="uploading")
        _broadcast_progress(db_task_id, 80, "uploading", "正在上传生成结果...")

        output = []
        total_cost = 0
        has_error = False
        error_msg = ""

        for r in results:
            rd = r.to_dict()
            from app.services.demo_tag import demo_mode_active, tag_result
            out = tag_result({
                "type": "image",
                "url": rd.get("media_url", ""),
                "model": rd.get("model", model),
                "resolution": rd.get("resolution", size),
                "cost": rd.get("cost", 0),
                "seed": seed,
            }, demo=demo_mode_active() or rd.get("demo"))
            if rd.get("error"):
                has_error = True
                error_msg = rd["error"]
                out["error"] = rd["error"]
            output.append(out)
            total_cost += rd.get("cost", 0)

        if has_error:
            return _mark_failed(db_task_id, error_msg or "Generation returned error")

        output = persist_results(output)
        output = _enforce_resolution(output, size)
        _update_task(
            db_task_id, status="completed", progress=100, current_stage="completed",
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(output), actual_cost=total_cost,
        )
        model_health.record_success(model, int((time.monotonic() - started) * 1000))
        _broadcast_progress(db_task_id, 100, "completed", "生成完成！")
        return {"status": "completed", "results": output, "cost": total_cost}

    except RuntimeError as e:
        from app.fallback_handler import is_retryable_error
        model_health.record_failure(model, str(e), retryable=is_retryable_error(str(e)))
        return _handle_retryable(self, db_task_id, model, str(e), "image", prompt, size, style, count)
    except Exception as e:
        from app.fallback_handler import is_retryable_error
        model_health.record_failure(model, str(e), retryable=is_retryable_error(str(e)))
        return _mark_failed(db_task_id, str(e))


def _handle_retryable(self, db_task_id, model, error, media_type, *args):
    """Check if error is retryable and try fallback."""
    from app.fallback_handler import get_fallback, is_retryable_error

    if not is_retryable_error(error):
        return _mark_failed(db_task_id, error)

    fallback_id = get_fallback(model)
    if not fallback_id:
        return _mark_failed(db_task_id, f"{error} (no fallback available)")

    logger.info(f"Retrying with fallback {fallback_id} for {model} failed: {error}")
    _update_task(db_task_id, current_stage="fallback_used", selected_model=fallback_id)
    self.update_state(state="PROGRESS", meta={"current_stage": "fallback", "progress": 40})

    get_adapter = _load_adapters()
    fb_adapter = get_adapter(fallback_id)
    if not fb_adapter:
        return _mark_failed(db_task_id, f"Fallback adapter not found: {fallback_id}")

    started = time.monotonic()
    try:
        kwargs = model.split("/")
        # Reconstruct call for fallback
        if media_type == "image":
            results = _run_async(
                fb_adapter.generate_image(
                    prompt=args[0], model_id=fallback_id,
                    size=args[1] if len(args) > 1 else "1024x1024",
                    style=args[2] if len(args) > 2 else "auto",
                    count=args[3] if len(args) > 3 else 1,
                )
            )
        else:
            results = _run_async(
                fb_adapter.generate_video(prompt=args[0], model_id=fallback_id)
            )

        # Normalize single-result adapters (e.g. KIE) to a list.
        if not isinstance(results, list):
            results = [results]
        quality_ok, quality_error = validate_generation_results(results, media_type)
        if not quality_ok:
            raise RuntimeError(quality_error)

        # ... process results (simplified)
        output = []
        total_cost = 0
        for r in results:
            rd = r.to_dict()
            output.append({
                "type": media_type, "url": rd.get("media_url", ""),
                "model": fallback_id, "cost": rd.get("cost", 0),
            })
            total_cost += rd.get("cost", 0)
            if rd.get("error"):
                return _mark_failed(db_task_id, rd["error"])

        output = persist_results(output)
        _update_task(
            db_task_id, status="completed", progress=100, current_stage="completed_fallback",
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(output), actual_cost=total_cost,
        )
        model_health.record_success(fallback_id, int((time.monotonic() - started) * 1000))
        return {"status": "completed_fallback", "results": output, "cost": total_cost}

    except Exception as fe:
        from app.fallback_handler import is_retryable_error
        model_health.record_failure(fallback_id, str(fe), retryable=is_retryable_error(str(fe)))
        return _mark_failed(db_task_id, f"Fallback also failed: {fe}. Original: {error}")


def _translate_error(error_msg: str) -> str:
    """Translate raw API errors to user-friendly Chinese messages."""
    err_lower = error_msg.lower()
    
    if any(w in err_lower for w in ("guardrails", "nudity", "sexuality", "erotic", "inappropriate", "content policy", "safety system")):
        return "内容不合规：您的提示词包含不当内容，已被 AI 安全系统拦截。请修改后重试。"
    if "violates" in err_lower:
        return "内容不合规：提示词违反了内容安全策略。请使用合规的描述重新尝试。"
    if "timeout" in err_lower or "timed out" in err_lower:
        return "生成超时：AI 模型响应时间过长，请稍后重试或简化提示词。"
    if "rate" in err_lower and ("limit" in err_lower or "exceeded" in err_lower):
        return "请求过于频繁：请稍等片刻后再试。"
    
    return error_msg


def _mark_failed(db_task_id: str, error_msg: str) -> dict:
    friendly_msg = _translate_error(error_msg)
    logger.error(f"Task {db_task_id} failed: {error_msg}")
    _update_task(
        db_task_id, status="failed", progress=0, current_stage="failed",
        error_message=friendly_msg, completed_at=datetime.now(timezone.utc),
    )
    return {"status": "failed", "error": friendly_msg}

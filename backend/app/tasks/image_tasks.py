"""
Image generation Celery tasks — calls real adapters with smart fallback.
"""
import json
import logging
import time
from datetime import datetime, timezone

from celery_app import app

from app.services.media_store import persist_results
from app.services.model_health import model_health, validate_generation_results

from app.tasks.common import broadcast_progress, chdir_backend_root, load_adapters, run_async, update_task

logger = logging.getLogger(__name__)


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
    chdir_backend_root()

    self.update_state(state="PROGRESS", meta={"current_stage": "routing", "progress": 10})
    update_task(
        db_task_id, status="generating", selected_model=model,
        progress=10, current_stage="routing",
        started_at=datetime.now(timezone.utc),
    )
    broadcast_progress(db_task_id, 10, "routing", "正在分析提示词并选择最优模型...")

    self.update_state(state="PROGRESS", meta={"current_stage": "generating", "progress": 30})
    update_task(db_task_id, progress=30, current_stage="generating")
    broadcast_progress(db_task_id, 30, "generating", "模型已选定，开始生成...")

    # Demo mode: render locally when no provider key is configured.
    from app.adapters.demo_provider import demo_mode_active, DemoAdapter
    if demo_mode_active():
        adapter = DemoAdapter(model_label=model)
    else:
        # Get adapter and fallback config
        get_adapter = load_adapters()
        adapter = get_adapter(model)
        if not adapter:
            # Try fallback
            from app.fallback_handler import get_fallback
            fallback_id = get_fallback(model)
            if fallback_id:
                adapter = get_adapter(fallback_id)
                model = fallback_id
                update_task(db_task_id, selected_model=model, current_stage="fallback_used")

        if not adapter:
            return _mark_failed(db_task_id, f"No adapter for model or fallback: {model}")

    size = params.get("size", params.get("resolution", "1024x1024"))
    style = params.get("style", "auto")
    count = params.get("count", 1)
    seed = params.get("seed")

    self.update_state(state="PROGRESS", meta={"current_stage": "generating", "progress": 50})
    update_task(db_task_id, progress=50)
    broadcast_progress(db_task_id, 50, "generating", "模型正在创作中，请稍候...")

    started = time.monotonic()
    try:
        result = run_async(
            adapter.generate_image(prompt=prompt, model_id=model, size=size, style=style, count=count, seed=seed)
        )
        # Adapt single GenerationResult to list for uniform processing
        results = [result] if not isinstance(result, list) else result
        quality_ok, quality_error = validate_generation_results(results, "image")
        if not quality_ok:
            raise RuntimeError(quality_error)

        self.update_state(state="PROGRESS", meta={"current_stage": "uploading", "progress": 80})
        update_task(db_task_id, progress=80, current_stage="uploading")
        broadcast_progress(db_task_id, 80, "uploading", "正在上传生成结果...")

        output = []
        total_cost = 0
        has_error = False
        error_msg = ""

        for r in results:
            rd = r.to_dict()
            out = {
                "type": "image",
                "url": rd.get("media_url", ""),
                "model": rd.get("model", model),
                "resolution": rd.get("resolution", size),
                "cost": rd.get("cost", 0),
                "seed": seed,
            }
            if rd.get("error"):
                has_error = True
                error_msg = rd["error"]
                out["error"] = rd["error"]
            output.append(out)
            total_cost += rd.get("cost", 0)

        if has_error:
            return _mark_failed(db_task_id, error_msg or "Generation returned error")

        output = persist_results(output)
        update_task(
            db_task_id, status="completed", progress=100, current_stage="completed",
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(output), actual_cost=total_cost,
        )
        model_health.record_success(model, int((time.monotonic() - started) * 1000))
        broadcast_progress(db_task_id, 100, "completed", "生成完成！")
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
    update_task(db_task_id, current_stage="fallback_used", selected_model=fallback_id)
    self.update_state(state="PROGRESS", meta={"current_stage": "fallback", "progress": 40})

    get_adapter = load_adapters()
    fb_adapter = get_adapter(fallback_id)
    if not fb_adapter:
        return _mark_failed(db_task_id, f"Fallback adapter not found: {fallback_id}")

    started = time.monotonic()
    try:
        kwargs = model.split("/")
        # Reconstruct call for fallback
        if media_type == "image":
            results = run_async(
                fb_adapter.generate_image(
                    prompt=args[0], model_id=fallback_id,
                    size=args[1] if len(args) > 1 else "1024x1024",
                    style=args[2] if len(args) > 2 else "auto",
                    count=args[3] if len(args) > 3 else 1,
                )
            )
        else:
            results = run_async(
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
        update_task(
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
    update_task(
        db_task_id, status="failed", progress=0, current_stage="failed",
        error_message=friendly_msg, completed_at=datetime.now(timezone.utc),
    )
    return {"status": "failed", "error": friendly_msg}

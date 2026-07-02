"""
Multi-step pipeline tasks — sequential image-to-video workflows.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from celery_app import app

logger = logging.getLogger(__name__)


def _get_db_url():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if db_url.startswith("sqlite+aiosqlite"):
        db_url = db_url.replace("sqlite+aiosqlite", "sqlite")
    elif db_url.startswith("postgresql+asyncpg"):
        db_url = db_url.replace("postgresql+asyncpg", "postgresql")
    return db_url


def _update_task(db_task_id: str, **kwargs):
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    db_url = _get_db_url()
    engine = create_engine(db_url)
    with Session(engine) as session:
        stmt = text("SELECT id FROM tasks WHERE task_id = :tid")
        row = session.execute(stmt, {"tid": db_task_id}).first()
        if not row:
            return None
        task_pk = row[0]
        for field, value in kwargs.items():
            if value is not None:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                session.execute(
                    text(f"UPDATE tasks SET {field} = :val WHERE id = :id"),
                    {"val": value, "id": task_pk},
                )
        session.commit()
        return task_pk


@app.task(
    bind=True,
    name="app.tasks.pipeline_tasks.run_pipeline",
    queue="pipeline_q",
    max_retries=3,
    acks_late=True,
)
def run_pipeline(
    self,
    db_task_id: str,
    pipeline_config: list[dict],
) -> dict:
    """Run a multi-step pipeline (image → video chain)."""
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    total_steps = len(pipeline_config)
    self.update_state(state="PROGRESS", meta={
        "current_stage": "routing",
        "progress": 5,
        "total_steps": total_steps,
        "current_step": 0,
    })
    _update_task(
        db_task_id,
        status="generating",
        progress=5,
        current_stage="routing",
        started_at=datetime.now(timezone.utc),
    )

    results = []
    total_cost = 0

    for i, step_config in enumerate(pipeline_config):
        step_type = step_config["step"]
        step_model = step_config["model"]
        step_prompt = step_config["prompt"]
        step_params = step_config.get("params", {})

        progress = int(10 + (i / max(total_steps, 1)) * 80)
        self.update_state(state="PROGRESS", meta={
            "current_stage": f"step_{i+1}_{step_type}",
            "progress": progress,
            "total_steps": total_steps,
            "current_step": i + 1,
        })
        _update_task(db_task_id, progress=progress, current_stage=f"step_{i+1}_{step_type}")

        # Pass previous step output if needed
        extra = {}
        if step_config.get("input_type") == "image" and results:
            last_url = results[-1].get("url")
            if last_url:
                extra["image_url"] = last_url

        params = {**step_params, **extra}

        if step_type == "image":
            step_result = _run_image(db_task_id, step_model, step_prompt, params)
        elif step_type == "video":
            step_result = _run_video(db_task_id, step_model, step_prompt, params)
        else:
            raise ValueError(f"Unknown step type: {step_type}")

        error = None
        for r in step_result.get("results", []):
            if r.get("error"):
                error = r.get("error")
                break
        if error:
            raise RuntimeError(f"Pipeline step {i+1} failed: {error}")

        results.extend(step_result.get("results", []))
        total_cost += step_result.get("cost", 0)

    _update_task(
        db_task_id,
        status="completed",
        progress=100,
        current_stage="completed",
        completed_at=datetime.now(timezone.utc),
        results=json.dumps(results),
        actual_cost=total_cost,
    )

    return {"status": "completed", "results": results, "cost": total_cost}


def _run_image(db_task_id, model, prompt, params):
    """Run image generation synchronously."""
    from app.adapters.registry import get_adapter, _load_all_adapters
    _load_all_adapters()
    adapter = get_adapter(model)
    if not adapter:
        raise RuntimeError(f"No adapter: {model}")

    size = params.get("size", params.get("resolution", "1024x1024"))
    style = params.get("style", "auto")
    count = params.get("count", 1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        raw_results = loop.run_until_complete(
            adapter.generate_image(prompt=prompt, size=size, style=style, count=count)
        )
    finally:
        loop.close()

    output = []
    cost = 0
    for r in raw_results:
        rd = r.to_dict()
        output.append({
            "type": "image", "url": rd["media_url"], "model": rd["model"],
            "resolution": rd["resolution"], "cost": rd["cost"], "error": rd.get("error"),
        })
        cost += rd.get("cost", 0)
    return {"results": output, "cost": cost}


def _run_video(db_task_id, model, prompt, params):
    """Run video generation synchronously."""
    from app.adapters.registry import get_adapter, _load_all_adapters
    _load_all_adapters()
    adapter = get_adapter(model)
    if not adapter:
        raise RuntimeError(f"No adapter: {model}")

    duration = params.get("duration", 5)
    resolution = params.get("resolution", "1080p")
    image_url = params.get("image_url")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            adapter.generate_video(
                prompt=prompt, image_url=image_url,
                duration=duration, resolution=resolution,
            )
        )
    finally:
        loop.close()

    rd = result.to_dict() if hasattr(result, "to_dict") else result
    output = [{
        "type": "video", "url": rd.get("media_url", ""),
        "thumbnail": rd.get("thumbnail_url", ""),
        "model": rd.get("model", model), "resolution": rd.get("resolution", resolution),
        "duration": rd.get("duration", duration), "cost": rd.get("cost", 0),
        "error": rd.get("error"),
    }]
    return {"results": output, "cost": rd.get("cost", 0)}

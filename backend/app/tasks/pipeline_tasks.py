"""
Multi-step pipeline tasks — sequential image-to-video workflows.
"""
import json
import logging
import os
from datetime import datetime, timezone

from celery_app import app

from app.services.media_store import persist_results
from app.tasks.common import load_adapters, run_async, update_task

logger = logging.getLogger(__name__)


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
    update_task(
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
        update_task(db_task_id, progress=progress, current_stage=f"step_{i+1}_{step_type}")

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

    results = persist_results(results)
    update_task(
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
    adapter = load_adapters()(model)
    if not adapter:
        raise RuntimeError(f"No adapter: {model}")

    size = params.get("size", params.get("resolution", "1024x1024"))
    style = params.get("style", "auto")
    count = params.get("count", 1)

    raw_results = run_async(
        adapter.generate_image(prompt=prompt, size=size, style=style, count=count)
    )

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
    adapter = load_adapters()(model)
    if not adapter:
        raise RuntimeError(f"No adapter: {model}")

    duration = params.get("duration", 5)
    resolution = params.get("resolution", "1080p")
    image_url = params.get("image_url")

    result = run_async(
        adapter.generate_video(
            prompt=prompt, image_url=image_url,
            duration=duration, resolution=resolution,
        )
    )

    rd = result.to_dict() if hasattr(result, "to_dict") else result
    output = [{
        "type": "video", "url": rd.get("media_url", ""),
        "thumbnail": rd.get("thumbnail_url", ""),
        "model": rd.get("model", model), "resolution": rd.get("resolution", resolution),
        "duration": rd.get("duration", duration), "cost": rd.get("cost", 0),
        "error": rd.get("error"),
    }]
    return {"results": output, "cost": rd.get("cost", 0)}

"""
Director async task — run a multi-shot storyboard in the background and stream
progress to Redis, so long real-model films (6 shots × ~150s = 15+ min) never
block an HTTP/SSE connection. The frontend polls GET /director/progress/<job_id>.
"""
import asyncio
import json
import logging
import os
import time

from celery_app import app

logger = logging.getLogger(__name__)

PROGRESS_PREFIX = "director:progress:"
PROGRESS_TTL = 3600  # 1h


def _redis():
    import redis
    from app.config import settings
    return redis.from_url(settings.REDIS_URL)


def _key(job_id: str) -> str:
    return f"{PROGRESS_PREFIX}{job_id}"


def write_progress(job_id: str, state: dict) -> None:
    try:
        r = _redis()
        r.set(_key(job_id), json.dumps(state, ensure_ascii=False), ex=PROGRESS_TTL)
    except Exception as e:  # pragma: no cover
        logger.warning("[director_task] progress write failed: %s", e)


def read_progress(job_id: str) -> dict | None:
    try:
        raw = _redis().get(_key(job_id))
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(name="app.tasks.director_tasks.run_director", queue="director_q",
          soft_time_limit=3600, time_limit=3900)
def run_director(job_id: str, plan_dict: dict, dry_run: bool, session_uid: str | None = None, user_id: int = 0):
    """Execute a director plan, persisting live per-step progress to Redis."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_dir not in os.getcwd():
        os.chdir(backend_dir)

    from app.director import plan_from_dict, DirectorExecutor

    plan = plan_from_dict(plan_dict)
    executor = DirectorExecutor(dry_run=dry_run)
    t0 = time.time()

    # Seed initial state (all steps pending / skipped).
    steps_state = {
        s.id: {"id": s.id, "status": "skipped" if s.skip else "pending",
               "title": s.title, "elapsed_ms": None}
        for s in plan.steps
    }
    assets: list[dict] = []

    def snapshot(status: str, done: bool = False, total_ms: int | None = None):
        write_progress(job_id, {
            "job_id": job_id, "status": status, "done": done,
            "user_id": user_id,
            "dry_run": dry_run, "plan": plan.to_dict(),
            "session_uid": session_uid,
            "steps": list(steps_state.values()), "assets": assets,
            "asset_count": len(assets), "total_ms": total_ms,
        })

    snapshot("running")

    async def _drive():
        async for ev in executor.run_stream(plan):
            t = ev.get("type")
            if t == "step_start":
                steps_state.setdefault(ev["id"], {"id": ev["id"]})
                steps_state[ev["id"]].update({"status": "running", "title": ev.get("title")})
                snapshot("running")
            elif t == "step_done":
                steps_state.setdefault(ev["id"], {"id": ev["id"]})
                steps_state[ev["id"]].update({"status": "done", "elapsed_ms": ev.get("elapsed_ms")})
                if ev.get("asset"):
                    assets.append(ev["asset"])
                snapshot("running")
            elif t == "step_error":
                if ev.get("id"):
                    steps_state.setdefault(ev["id"], {"id": ev["id"]})
                    steps_state[ev["id"]].update({"status": "failed", "elapsed_ms": ev.get("elapsed_ms")})
                snapshot("running")
            elif t == "complete":
                snapshot("done", done=True, total_ms=ev.get("total_ms"))

    try:
        _run_async(_drive())
    except Exception as e:
        logger.exception("[director_task] run failed: %s", e)
        write_progress(job_id, {"job_id": job_id, "status": "failed", "done": True,
                                 "user_id": user_id, "session_uid": session_uid,
                                 "error": str(e), "steps": list(steps_state.values()),
                                 "assets": assets, "asset_count": len(assets)})
        return {"status": "failed", "error": str(e)}

    total_ms = int((time.time() - t0) * 1000)
    # Persist to the session row (best-effort) so it shows on /sessions.
    if session_uid:
        try:
            _persist_session(session_uid, plan.to_dict(), assets)
        except Exception as e:
            logger.warning("[director_task] session persist failed: %s", e)

    return {"status": "done", "asset_count": len(assets), "total_ms": total_ms}


def _persist_session(session_uid: str, plan: dict, assets: list):
    """Sync-write the finished plan+assets into the DirectorSession row."""
    from sqlalchemy import create_engine, text
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    db_url = db_url.replace("sqlite+aiosqlite", "sqlite").replace("postgresql+asyncpg", "postgresql")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE director_sessions SET plan=:p, assets=:a, status='done', updated_at=CURRENT_TIMESTAMP WHERE session_uid=:u"),
            {"p": json.dumps(plan, ensure_ascii=False), "a": json.dumps(assets, ensure_ascii=False), "u": session_uid},
        )

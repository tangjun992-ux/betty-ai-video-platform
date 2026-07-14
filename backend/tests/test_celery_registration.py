"""Guard: every dispatched Celery task must be registered on a worker.

Regression test for the class of bug where a task module defines ``@app.task``
but is missing from ``celery_app.include`` — the API can call ``.delay()`` but
no worker ever registers the task, so the job hangs forever.

It also asserts every task routes to a queue that at least one documented worker
listens on, so dev/prod ``docker-compose`` worker ``-Q`` lists cannot silently
drift away from the routing table.
"""
import re
from pathlib import Path

import pytest

# Tasks the product actually dispatches via .delay()/apply_async, and the queue
# they are expected to run on. Keep in sync with app.api.* dispatch sites.
EXPECTED_TASKS = {
    "app.tasks.image_tasks.generate_image": "image_q",
    "app.tasks.video_tasks.generate_video": "video_q",
    "app.tasks.pipeline_tasks.run_pipeline": "pipeline_q",
    "app.tasks.director_tasks.run_director": "director_q",
    "app.tasks.lipsync_tasks.process_lipsync": "video_q",
    "app.tasks.motion_tasks.process_motion_task": "video_q",
    "app.tasks.timeline_tasks.process_timeline_render": "pipeline_q",
}

# Queues each worker process listens on (must match docker-compose -Q lists).
DEV_WORKER_QUEUES = {"video_q", "image_q", "pipeline_q", "director_q", "celery"}
DEV_COLLECTOR_QUEUES = {"collector_q"}
PROD_WORKER_QUEUES = {
    "celery", "image_q", "video_q", "director_q", "pipeline_q", "collector_q",
}


@pytest.fixture(scope="module")
def celery_app():
    from celery_app import app
    # A real worker registers tasks by importing every module in `include`
    # on boot; replicate that here so the test reflects worker behaviour.
    app.loader.import_default_modules()
    return app


def test_all_dispatched_tasks_are_registered(celery_app):
    """Worker would register every task the API dispatches."""
    registered = set(celery_app.tasks.keys())
    missing = [name for name in EXPECTED_TASKS if name not in registered]
    assert not missing, (
        f"Tasks not registered on the worker (add their module to "
        f"celery_app.include): {missing}"
    )


def test_tasks_route_to_expected_queue(celery_app):
    """The routing table sends each task to the queue we expect."""
    from kombu.utils.functional import maybe_evaluate  # noqa: F401 (ensure kombu present)

    for name, expected_q in EXPECTED_TASKS.items():
        route = celery_app.amqp.router.route({}, name)
        queue = route.get("queue")
        # Celery may resolve to a Queue object or a name depending on version.
        queue_name = getattr(queue, "name", queue)
        assert queue_name == expected_q, (
            f"{name} routes to {queue_name!r}, expected {expected_q!r}"
        )


def test_every_expected_queue_has_a_listening_worker():
    """No task may route to a queue that no worker process consumes."""
    used_queues = set(EXPECTED_TASKS.values())
    dev_covers = DEV_WORKER_QUEUES | DEV_COLLECTOR_QUEUES
    prod_covers = PROD_WORKER_QUEUES

    dev_gap = used_queues - dev_covers
    prod_gap = used_queues - prod_covers
    assert not dev_gap, f"dev workers do not consume queues: {dev_gap}"
    assert not prod_gap, f"prod worker does not consume queues: {prod_gap}"


def test_compose_worker_queue_lists_match_routing():
    """docker-compose worker -Q lists cover every routed queue (guards drift)."""
    repo = Path(__file__).resolve().parents[2]
    used_queues = set(EXPECTED_TASKS.values())

    def worker_queues(compose_path: Path) -> set[str]:
        text = compose_path.read_text(encoding="utf-8")
        qs: set[str] = set()
        for m in re.finditer(r"celery -A celery_app worker[^\n]*?-Q\s+([\w,]+)", text):
            qs |= set(m.group(1).split(","))
        return qs

    dev = worker_queues(repo / "docker-compose.yml")
    prod = worker_queues(repo / "docker-compose.prod.yml")

    assert used_queues - dev == set(), (
        f"docker-compose.yml workers miss queues: {used_queues - dev}"
    )
    assert used_queues - prod == set(), (
        f"docker-compose.prod.yml worker misses queues: {used_queues - prod}"
    )

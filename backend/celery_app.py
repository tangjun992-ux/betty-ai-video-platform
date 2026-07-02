from celery import Celery
import os

app = Celery(
    "aivideo",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/2",
    include=[
        "app.tasks.image_tasks",
        "app.tasks.video_tasks",
        "app.tasks.pipeline_tasks",
        "app.collector.tasks",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=7200,
    task_routes={
        "app.tasks.image_tasks.*": {"queue": "image_q"},
        "app.tasks.video_tasks.*": {"queue": "video_q"},
        "app.tasks.pipeline_tasks.*": {"queue": "pipeline_q"},
        "app.collector.tasks.*": {"queue": "collector_q"},
    },
    broker_connection_retry_on_startup=True,
    task_default_retry_delay=10,
    task_max_retries=3,
    worker_max_tasks_per_child=100,
    worker_max_memory_per_child=500000,
    task_soft_time_limit=600,
    task_time_limit=900,
    beat_schedule={
        # Reddit: every 10 minutes (tech)
        "collect-reddit-tech": {
            "task": "app.collector.tasks.collect_reddit",
            "schedule": 600.0,
            "kwargs": {"category": "tech", "limit": 25},
            "options": {"queue": "collector_q"},
        },
        # Reddit: every 15 minutes (entertainment)
        "collect-reddit-entertainment": {
            "task": "app.collector.tasks.collect_reddit",
            "schedule": 900.0,
            "kwargs": {"category": "entertainment", "limit": 25},
            "options": {"queue": "collector_q"},
        },
        # YouTube: every 15 minutes
        "collect-youtube-trending": {
            "task": "app.collector.tasks.collect_youtube",
            "schedule": 900.0,
            "kwargs": {"limit": 25},
            "options": {"queue": "collector_q"},
        },
        # TikTok: every 30 minutes
        "collect-tiktok-trending": {
            "task": "app.collector.tasks.collect_tiktok",
            "schedule": 1800.0,
            "kwargs": {"region": "US", "limit": 25},
            "options": {"queue": "collector_q"},
        },
        # X: every 20 minutes
        "collect-x-trending": {
            "task": "app.collector.tasks.collect_x",
            "schedule": 1200.0,
            "kwargs": {"limit": 25},
            "options": {"queue": "collector_q"},
        },
        # Daily report: every 24h
        "generate-daily-report": {
            "task": "app.collector.tasks.generate_daily_report",
            "schedule": 86400.0,
            "kwargs": {"period": "daily"},
            "options": {"queue": "collector_q"},
        },
        # Cleanup: every 24h
        "cleanup-old-topics": {
            "task": "app.collector.tasks.cleanup_old_topics",
            "schedule": 86400.0,
            "kwargs": {"days": 7},
            "options": {"queue": "collector_q"},
        },
    } if os.getenv("VIS_COLLECTION_AUTO", "true").lower() == "true" else {},
)

if __name__ == "__main__":
    app.start()

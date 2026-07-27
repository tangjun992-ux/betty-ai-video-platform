"""
Celery Beat schedule for VIS — Periodic collection and reporting.
"""
from celery.schedules import crontab
from celery_app import app

# ── Beat Schedule ──
app.conf.beat_schedule = {
    # Reddit: every 10 minutes
    "collect-reddit-tech": {
        "task": "app.collector.tasks.collect_reddit",
        "schedule": crontab(minute="*/10"),
        "kwargs": {"category": "tech", "limit": 25},
        "options": {"queue": "collector_q"},
    },
    "collect-reddit-entertainment": {
        "task": "app.collector.tasks.collect_reddit",
        "schedule": crontab(minute="*/15"),
        "kwargs": {"category": "entertainment", "limit": 25},
        "options": {"queue": "collector_q"},
    },
    "collect-reddit-news": {
        "task": "app.collector.tasks.collect_reddit",
        "schedule": crontab(minute="*/15"),
        "kwargs": {"category": "news", "limit": 20},
        "options": {"queue": "collector_q"},
    },

    # YouTube: every 15 minutes
    "collect-youtube-trending": {
        "task": "app.collector.tasks.collect_youtube",
        "schedule": crontab(minute="*/15"),
        "kwargs": {"limit": 25},
        "options": {"queue": "collector_q"},
    },

    # Daily report: every day at 08:00 Asia/Shanghai
    "generate-daily-report": {
        "task": "app.collector.tasks.generate_daily_report",
        "schedule": crontab(hour=8, minute=0),
        "kwargs": {"period": "daily"},
        "options": {"queue": "collector_q"},
    },

    # Hourly report summary
    "generate-hourly-report": {
        "task": "app.collector.tasks.generate_daily_report",
        "schedule": crontab(minute=0),
        "kwargs": {"period": "hourly"},
        "options": {"queue": "collector_q"},
    },

    # Cleanup: every day at 03:00
    "cleanup-old-topics": {
        "task": "app.collector.tasks.cleanup_old_topics",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"days": 7},
        "options": {"queue": "collector_q"},
    },
}

# Timezone
app.conf.timezone = "Asia/Shanghai"
app.conf.enable_utc = True

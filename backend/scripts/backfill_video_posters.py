"""
One-off: give existing completed video tasks a real JPEG first-frame poster.

Older rows stored the video file itself (or a provider .mp4 cover) as the
`thumbnail`, which can't render inside an <img>. This extracts a poster with
ffmpeg for any video result whose thumbnail is missing/points at a video file.

    cd backend && source .venv/bin/activate && \
        STORAGE_PATH=/tmp/aivideo-media python scripts/backfill_video_posters.py
"""
import json
import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.media_store import extract_video_poster, _VIDEO_EXTS


def _sync_db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    return url.replace("sqlite+aiosqlite", "sqlite").replace("postgresql+asyncpg", "postgresql")


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    engine = create_engine(_sync_db_url())
    fixed = 0
    with Session(engine) as s:
        rows = s.execute(text(
            "SELECT id, results FROM tasks WHERE status='completed' AND media_type='video'"
        )).fetchall()
        for rid, results in rows:
            try:
                data = json.loads(results) if isinstance(results, str) else results
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            changed = False
            for r in data:
                if not isinstance(r, dict):
                    continue
                url = r.get("url") or r.get("media_url") or ""
                thumb = r.get("thumbnail") or ""
                ext = os.path.splitext(urlparse(thumb).path)[1].lower()
                if url and (not thumb or thumb == url or ext in _VIDEO_EXTS):
                    poster = extract_video_poster(url)
                    if poster:
                        r["thumbnail"] = poster
                        changed = True
            if changed:
                s.execute(text("UPDATE tasks SET results=:r WHERE id=:id"),
                          {"r": json.dumps(data), "id": rid})
                fixed += 1
        s.commit()
    print(f"Backfilled posters for {fixed} video task(s).")


if __name__ == "__main__":
    main()

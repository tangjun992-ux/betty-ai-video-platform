#!/usr/bin/env python3
"""
Backup — snapshot the database + a media manifest into a timestamped archive.

Usage:
    python scripts/backup.py [--out /path/to/backups]

- SQLite: copies the DB file (consistent via the online backup API).
- Postgres: runs pg_dump if available (needs pg_dump on PATH + DATABASE_URL).
- Media: writes a manifest (path,size,mtime) of STORAGE_LOCAL_PATH so a media
  sync (rsync/S3) can be validated. Object-store media (S3) is backed up by the
  bucket's own versioning/replication and is skipped here.

Intended to run from cron, e.g. daily:
    0 3 * * *  cd /app && python scripts/backup.py >> /var/log/betty-backup.log 2>&1
"""
import argparse
import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def backup_sqlite(db_path: str, dest_dir: Path) -> Path | None:
    if not os.path.exists(db_path):
        print(f"[backup] sqlite file not found: {db_path}")
        return None
    out = dest_dir / "database.sqlite"
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(str(out))
    with dst:
        src.backup(dst)  # consistent online snapshot
    src.close(); dst.close()
    # gzip it
    gz = dest_dir / "database.sqlite.gz"
    with open(out, "rb") as f_in, gzip.open(gz, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    out.unlink()
    print(f"[backup] sqlite snapshot → {gz.name} ({gz.stat().st_size} bytes)")
    return gz


def backup_postgres(db_url: str, dest_dir: Path) -> Path | None:
    if not shutil.which("pg_dump"):
        print("[backup] pg_dump not found — skipping DB dump (configure pg_dump in prod)")
        return None
    out = dest_dir / "database.sql.gz"
    url = db_url.replace("postgresql+asyncpg", "postgresql")
    try:
        with gzip.open(out, "wb") as f:
            p = subprocess.run(["pg_dump", url], stdout=subprocess.PIPE, check=True)
            f.write(p.stdout)
        print(f"[backup] postgres dump → {out.name}")
        return out
    except Exception as e:
        print(f"[backup] pg_dump failed: {e}")
        return None


def media_manifest(media_root: str, dest_dir: Path) -> Path:
    root = Path(media_root)
    entries, total = [], 0
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file():
                st = p.stat()
                entries.append({"path": str(p.relative_to(root)), "size": st.st_size, "mtime": int(st.st_mtime)})
                total += st.st_size
    out = dest_dir / "media-manifest.json"
    out.write_text(json.dumps({"root": str(root), "count": len(entries),
                               "total_bytes": total, "files": entries}, ensure_ascii=False))
    print(f"[backup] media manifest → {out.name} ({len(entries)} files, {total/1e6:.1f} MB)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.getenv("BACKUP_DIR", "/tmp/betty-backups"))
    args = ap.parse_args()

    stamp = _ts()
    work = Path(args.out) / stamp
    work.mkdir(parents=True, exist_ok=True)

    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite"):
        path = db_url.split("///")[-1]
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
        backup_sqlite(path, work)
    else:
        backup_postgres(db_url, work)

    media_manifest(settings.STORAGE_LOCAL_PATH, work)

    # Bundle into a single archive + write a metadata file.
    meta = {"created_at": datetime.now(timezone.utc).isoformat(), "version": settings.APP_VERSION,
            "db": "sqlite" if db_url.startswith("sqlite") else "postgres",
            "storage_type": settings.STORAGE_TYPE}
    (work / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))

    archive = Path(args.out) / f"betty-backup-{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(work, arcname=stamp)
    shutil.rmtree(work, ignore_errors=True)
    print(f"[backup] DONE → {archive} ({archive.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

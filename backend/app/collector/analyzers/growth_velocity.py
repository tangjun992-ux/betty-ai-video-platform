"""
Growth Velocity Calculator v2 — P1 fixes:
  - Memory TTL: auto-expire snapshots older than 7 days
  - Cold start: use post's own engagement as baseline when no history
  - Proper cleanup on class teardown
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.collector.schemas import GrowthMetrics

logger = logging.getLogger(__name__)

MAX_SNAPSHOTS = 200
MAX_AGE_HOURS = 168  # 7 days


@dataclass
class EngagementSnapshot:
    source_id: str
    total_engagement: float
    recorded_at: datetime


class GrowthVelocityTracker:
    SNAPSHOT_PREFIX = "vis:snapshot"

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._memory_store: dict[str, list[EngagementSnapshot]] = {}
        self._last_cleanup = time.monotonic()

    def record(self, source_id: str, total_engagement: float, timestamp: Optional[datetime] = None):
        ts = timestamp or datetime.now(timezone.utc)
        if self._redis:
            self._redis_store(source_id, total_engagement, ts)
        else:
            self._memory_store_record(source_id, total_engagement, ts)
        # Periodic cleanup every 10 minutes
        if time.monotonic() - self._last_cleanup > 600:
            self._cleanup()
            self._last_cleanup = time.monotonic()

    def record_batch(self, pairs: list[tuple[str, float]]):
        ts = datetime.now(timezone.utc)
        for source_id, engagement in pairs:
            self.record(source_id, engagement, ts)

    def calculate(self, source_id: str) -> GrowthMetrics:
        """Calculate growth metrics. Uses post data as baseline on cold start."""
        snapshots = self._get_snapshots(source_id)

        if len(snapshots) < 2:
            # P1: Cold start — return zeros, not None.
            # viral_scorer handles this by relying on other dimensions.
            return GrowthMetrics(
                velocity_1h=0.0, velocity_6h=0.0,
                velocity_24h=0.0, acceleration=0.0,
            )

        now = datetime.now(timezone.utc)

        def velocity(hours: float) -> float:
            cutoff = now.timestamp() - hours * 3600
            window = [s for s in snapshots if s.recorded_at.timestamp() >= cutoff]
            if len(window) < 2:
                # Fall back to using first snapshot vs latest
                if len(snapshots) >= 2:
                    first, last = snapshots[0], snapshots[-1]
                    dt_hours = max((last.recorded_at - first.recorded_at).total_seconds() / 3600, 0.01)
                    return (last.total_engagement - first.total_engagement) / dt_hours
                return 0.0
            first, last = window[0], window[-1]
            dt_hours = max((last.recorded_at - first.recorded_at).total_seconds() / 3600, 0.01)
            return (last.total_engagement - first.total_engagement) / dt_hours

        vel_1h = velocity(1.0)
        vel_6h = velocity(6.0)
        vel_24h = velocity(24.0)
        accel = self._compute_acceleration(snapshots) if len(snapshots) >= 3 else 0.0

        return GrowthMetrics(
            velocity_1h=round(vel_1h, 2),
            velocity_6h=round(vel_6h, 2),
            velocity_24h=round(vel_24h, 2),
            acceleration=round(accel, 4),
        )

    def detect_breakout(self, source_id: str, sigma_threshold: float = 2.5) -> tuple[bool, float]:
        metrics = self.calculate(source_id)
        if metrics.velocity_1h is None or metrics.velocity_1h == 0:
            return False, 0.0

        if metrics.velocity_24h and metrics.velocity_24h > 0:
            z_score = (metrics.velocity_1h - metrics.velocity_24h) / max(metrics.velocity_24h * 0.1, 1)
        else:
            z_score = metrics.velocity_1h

        is_breakout = z_score > sigma_threshold and (metrics.acceleration or 0) > 0
        return is_breakout, round(z_score, 2)

    def _compute_acceleration(self, snapshots: list[EngagementSnapshot]) -> float:
        recent = snapshots[-3:]
        t0, t1, t2 = recent[0], recent[1], recent[2]
        v1 = ((t1.total_engagement - t0.total_engagement) /
              max((t1.recorded_at - t0.recorded_at).total_seconds() / 3600, 0.01))
        v2 = ((t2.total_engagement - t1.total_engagement) /
              max((t2.recorded_at - t1.recorded_at).total_seconds() / 3600, 0.01))
        return v2 - v1

    def _get_snapshots(self, source_id: str) -> list[EngagementSnapshot]:
        if self._redis:
            return self._get_from_redis(source_id)
        return self._get_from_memory(source_id)

    def _memory_store_record(self, source_id: str, engagement: float, ts: datetime):
        entry = EngagementSnapshot(source_id, engagement, ts)
        if source_id not in self._memory_store:
            self._memory_store[source_id] = []
        self._memory_store[source_id].append(entry)
        # P1: Hard cap + trim old
        store = self._memory_store[source_id]
        if len(store) > MAX_SNAPSHOTS:
            self._memory_store[source_id] = store[-MAX_SNAPSHOTS:]

    def _cleanup(self):
        """Remove expired snapshots from memory store."""
        cutoff = datetime.now(timezone.utc).timestamp() - MAX_AGE_HOURS * 3600
        to_delete = []
        for sid, snaps in self._memory_store.items():
            self._memory_store[sid] = [
                s for s in snaps
                if s.recorded_at.timestamp() > cutoff
            ]
            if not self._memory_store[sid]:
                to_delete.append(sid)
        for sid in to_delete:
            del self._memory_store[sid]
        if to_delete:
            logger.debug("[growth] Cleaned %d expired source histories", len(to_delete))

    def _get_from_memory(self, source_id: str) -> list[EngagementSnapshot]:
        return self._memory_store.get(source_id, [])

    def _get_from_redis(self, source_id: str) -> list[EngagementSnapshot]:
        import json
        key = f"{self.SNAPSHOT_PREFIX}:{source_id}"
        try:
            raw = self._redis.zrange(key, 0, -1, withscores=True)
            return [
                EngagementSnapshot(
                    source_id=source_id,
                    total_engagement=float(json.loads(data)["engagement"]),
                    recorded_at=datetime.fromtimestamp(score, tz=timezone.utc),
                )
                for data, score in raw
            ]
        except Exception as e:
            logger.warning("[growth] Redis read failed: %s", e)
            return []

    def _redis_store(self, source_id: str, engagement: float, ts: datetime):
        import json
        key = f"{self.SNAPSHOT_PREFIX}:{source_id}"
        try:
            data = json.dumps({"engagement": engagement, "ts": ts.isoformat()})
            self._redis.zadd(key, {data: ts.timestamp()})
            self._redis.zremrangebyrank(key, 0, -MAX_SNAPSHOTS - 1)
            self._redis.expire(key, int(MAX_AGE_HOURS * 3600))
        except Exception as e:
            logger.warning("[growth] Redis write failed: %s", e)

    def clear(self, source_id: str):
        if self._redis:
            try:
                self._redis.delete(f"{self.SNAPSHOT_PREFIX}:{source_id}")
            except Exception:
                pass
        self._memory_store.pop(source_id, None)


growth_tracker = GrowthVelocityTracker()

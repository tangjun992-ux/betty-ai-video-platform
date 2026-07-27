"""Redis Streams integration for VIS pipeline."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Stream names
STREAMS = {
    "raw_posts": "vis:stream:raw_posts",
    "analyzed": "vis:stream:analyzed",
    "breakouts": "vis:stream:breakouts",
    "prompts": "vis:stream:prompts",
}

# Consumer groups
GROUPS = {
    "analyzers": "vis:group:analyzers",
    "prompt_gen": "vis:group:prompts",
}


class VISTransport:
    """Redis Streams transport layer for VIS pipeline.

    Producer → Stream → Consumer Group pattern.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._enabled = redis_client is not None

    def publish_raw_post(self, post_dict: dict) -> Optional[str]:
        """Publish a raw post to the analysis stream."""
        return self._publish(STREAMS["raw_posts"], {
            "event": "raw_post",
            "data": post_dict,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def publish_analyzed(self, topic_dict: dict) -> Optional[str]:
        """Publish an analyzed topic result."""
        return self._publish(STREAMS["analyzed"], {
            "event": "topic_analyzed",
            "data": topic_dict,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def publish_breakout(self, topic_dict: dict) -> Optional[str]:
        """Publish a breakout alert."""
        return self._publish(STREAMS["breakouts"], {
            "event": "breakout_detected",
            "data": topic_dict,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def publish_prompt(self, prompt_dict: dict) -> Optional[str]:
        """Publish a generated prompt."""
        return self._publish(STREAMS["prompts"], {
            "event": "prompt_generated",
            "data": prompt_dict,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def consume_analysis_stream(self, consumer_name: str, count: int = 10, block_ms: int = 5000):
        """Consumer: read from analysis queue."""
        if not self._enabled:
            return []
        try:
            self._ensure_group(STREAMS["raw_posts"], GROUPS["analyzers"])
            results = self._redis.xreadgroup(
                GROUPS["analyzers"], consumer_name,
                {STREAMS["raw_posts"]: ">"},
                count=count, block=block_ms,
            )
            items = []
            for stream_name, messages in results:
                for msg_id, fields in messages:
                    items.append({
                        "id": msg_id,
                        "data": json.loads(fields.get(b"data", b"{}")),
                        "event": fields.get(b"event", b"").decode(),
                    })
                    self._redis.xack(STREAMS["raw_posts"], GROUPS["analyzers"], msg_id)
            return items
        except Exception as e:
            logger.warning("[streams] Consumer error: %s", e)
            return []

    def _publish(self, stream: str, data: dict) -> Optional[str]:
        if not self._enabled:
            return None
        try:
            msg_id = self._redis.xadd(stream, {
                "data": json.dumps(data.get("data", {})),
                "event": data.get("event", "unknown"),
                "timestamp": data["timestamp"],
            }, maxlen=10000)
            return msg_id
        except Exception as e:
            logger.warning("[streams] Publish error: %s", e)
            return None

    def _ensure_group(self, stream: str, group: str):
        """Create consumer group if not exists."""
        try:
            self._redis.xgroup_create(stream, group, id="0", mkstream=True)
        except Exception:
            pass  # Group already exists

    def get_stream_info(self, stream: str) -> dict:
        """Get stream metadata."""
        if not self._enabled:
            return {"enabled": False}
        try:
            info = self._redis.xinfo_stream(stream)
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "groups": info.get("groups", 0),
            }
        except Exception:
            return {"length": 0, "error": "stream not found"}

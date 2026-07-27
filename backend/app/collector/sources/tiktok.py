"""
TikTok Source — Uses Apify TikTok actors for content collection.

Actors available (no login required):
  - clockworks/tiktok-scraper: Hashtag, user, video scraping
  - clockworks/tiktok-trending: Trending videos by region
  - curved/tiktok-data-extractor: Profile + video data

Falls back gracefully when Apify token unavailable.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.collector.sources.base import BaseSource, CollectResult
from app.collector.schemas import RawPost

logger = logging.getLogger(__name__)


class TikTokSource(BaseSource):
    """Collect trending TikTok content via Apify."""

    source_name = "tiktok"

    # Apify actor IDs
    ACTOR_TRENDING = "clockworks/tiktok-trending"
    ACTOR_SCRAPER = "clockworks/tiktok-scraper"

    # Default regions for trending
    DEFAULT_REGIONS = ["US", "GB", "JP", "KR", "BR"]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._token = os.getenv("TIKTOK_APIFY_TOKEN", "") or os.getenv("APIFY_TOKEN", "")
        self._base_url = "https://api.apify.com/v2"
        if not self._token:
            logger.warning("[tiktok] No TIKTOK_APIFY_TOKEN — TikTok collection disabled")

    async def collect(
        self,
        region: str = "US",
        regions: Optional[list[str]] = None,
        limit: int = 25,
        count: int = 50,
        scrape_type: str = "trending",  # trending | hashtag | user
        hashtag: Optional[str] = None,
        username: Optional[str] = None,
    ) -> CollectResult:
        """Collect TikTok content.

        Args:
            region: Single region code (US, GB, JP...)
            regions: Multiple regions
            limit: Videos to return
            count: Videos to fetch from Apify
            scrape_type: trending | hashtag | user
            hashtag: Hashtag to scrape (for scrape_type=hashtag)
            username: User to scrape (for scrape_type=user)
        """
        if not self._token:
            return CollectResult(
                source="tiktok", posts=[],
                error="No TIKTOK_APIFY_TOKEN configured",
            )

        target_regions = regions or [region]
        all_posts: list[RawPost] = []

        for reg in target_regions[:3]:  # Max 3 regions to avoid timeout
            try:
                if scrape_type == "trending":
                    posts = await self._collect_trending(reg, count)
                elif scrape_type == "hashtag" and hashtag:
                    posts = await self._collect_hashtag(hashtag, count)
                elif scrape_type == "user" and username:
                    posts = await self._collect_user(username, count)
                else:
                    posts = await self._collect_trending(reg, count)

                all_posts.extend(posts)
            except Exception as e:
                logger.warning("[tiktok] Region %s failed: %s", reg, e)
                continue

        # Deduplicate
        seen = set()
        unique = []
        for p in all_posts:
            if p.source_id not in seen:
                seen.add(p.source_id)
                unique.append(p)

        result = unique[:limit]
        logger.info("[tiktok] Collected %d videos from %d regions", len(result), len(target_regions))
        return CollectResult(source="tiktok", posts=result)

    async def _collect_trending(self, region: str, count: int) -> list[RawPost]:
        """Collect trending videos for a region."""
        run_id = await self._start_actor(self.ACTOR_TRENDING, {
            "region": region,
            "maxResults": min(count, 100),
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        })

        if not run_id:
            return []

        items = await self._wait_for_results(run_id)
        return [self._item_to_raw(item, region) for item in items]

    async def _collect_hashtag(self, hashtag: str, count: int) -> list[RawPost]:
        """Collect videos for a hashtag."""
        run_id = await self._start_actor(self.ACTOR_SCRAPER, {
            "hashtags": [hashtag],
            "maxVideosPerHashtag": min(count, 50),
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        })

        if not run_id:
            return []

        items = await self._wait_for_results(run_id)
        return [self._item_to_raw(item) for item in items]

    async def _collect_user(self, username: str, count: int) -> list[RawPost]:
        """Collect videos from a user profile."""
        run_id = await self._start_actor(self.ACTOR_SCRAPER, {
            "profiles": [username],
            "maxVideosPerProfile": min(count, 50),
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        })

        if not run_id:
            return []

        items = await self._wait_for_results(run_id)
        return [self._item_to_raw(item) for item in items]

    async def _start_actor(self, actor_id: str, input_data: dict) -> Optional[str]:
        """Start an Apify actor run. Returns run ID."""
        import urllib.request

        url = f"{self._base_url}/acts/{actor_id}/runs?token={self._token}"
        data = json.dumps(input_data).encode()

        loop = asyncio.get_event_loop()

        def _post():
            req = urllib.request.Request(url, data=data, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())

        try:
            result = await loop.run_in_executor(None, _post)
            run_id = result.get("data", {}).get("id")
            logger.info("[tiktok] Started actor %s run %s", actor_id, run_id)
            return run_id
        except Exception as e:
            logger.warning("[tiktok] Failed to start actor %s: %s", actor_id, e)
            return None

    async def _wait_for_results(self, run_id: str, max_wait: int = 120) -> list[dict]:
        """Poll for actor run completion and fetch results."""
        import urllib.request

        url = f"{self._base_url}/acts/{self.ACTOR_TRENDING}/runs/{run_id}?token={self._token}"

        loop = asyncio.get_event_loop()

        def _check():
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())

        # Poll for completion
        for _ in range(max_wait // 5):
            await asyncio.sleep(5)
            try:
                status = await loop.run_in_executor(None, _check)
                run_status = status.get("data", {}).get("status")
                if run_status == "SUCCEEDED":
                    break
                elif run_status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    logger.warning("[tiktok] Run %s: %s", run_id, run_status)
                    return []
            except Exception:
                continue

        # Fetch results
        results_url = f"{self._base_url}/actor-runs/{run_id}/dataset/items?token={self._token}"

        def _fetch():
            req = urllib.request.Request(results_url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())

        try:
            items = await loop.run_in_executor(None, _fetch)
            return items if isinstance(items, list) else items.get("data", items.get("items", []))
        except Exception as e:
            logger.warning("[tiktok] Failed to fetch results for %s: %s", run_id, e)
            return []

    def _item_to_raw(self, item: dict, region: Optional[str] = None) -> RawPost:
        """Convert Apify TikTok item to normalized RawPost."""
        vid = item.get("id", item.get("videoId", ""))
        web_url = item.get("webVideoUrl", item.get("url", ""))
        if not web_url and vid:
            web_url = f"https://www.tiktok.com/@/video/{vid}"

        # Parse timestamp
        created = None
        ts = item.get("createTime", item.get("createTimeISO"))
        if ts:
            try:
                if isinstance(ts, (int, float)):
                    created = datetime.fromtimestamp(ts, tz=timezone.utc)
                elif isinstance(ts, str):
                    created = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Author info
        author = None
        author_meta = item.get("authorMeta", item.get("author", {}))
        if isinstance(author_meta, dict):
            author = author_meta.get("nickName", author_meta.get("name"))

        # Description (TikTok captions often have hashtags)
        desc = item.get("text", item.get("description", ""))

        # Music info (useful for trend detection)
        music = item.get("musicMeta", {})
        music_name = music.get("musicName", "") if isinstance(music, dict) else ""

        # Stats
        stats = item.get("playCount", item.get("stats", {}))
        if isinstance(stats, dict):
            views = int(stats.get("playCount", 0))
            likes = int(stats.get("diggCount", 0))
            comments = int(stats.get("commentCount", 0))
            shares = int(stats.get("shareCount", 0))
        else:
            views = int(stats) if stats else 0
            likes = int(item.get("diggCount", 0))
            comments = int(item.get("commentCount", 0))
            shares = int(item.get("shareCount", 0))

        return RawPost(
            source_platform="tiktok",
            source_id=f"tt_{vid}" if vid else f"tt_{hash(web_url)}",
            source_url=web_url,
            title=desc[:200] if desc else "TikTok Video",
            description=f"{desc}\nMusic: {music_name}" if music_name else desc,
            author=author,
            thumbnail_url=item.get("covers", {}).get("default", item.get("videoCover", "")),
            category=region,
            upvotes=likes,
            comments=comments,
            shares=shares,
            views=views,
            source_created_at=created,
            raw_data={
                "video_id": vid,
                "music": music_name,
                "hashtags": [t.get("name") for t in item.get("hashtags", [])] if isinstance(item.get("hashtags"), list) else [],
                "mentions": item.get("mentions", []),
                "duration": item.get("videoMeta", {}).get("duration") if isinstance(item.get("videoMeta"), dict) else None,
                "region": region,
            },
        )


tiktok_source = TikTokSource()

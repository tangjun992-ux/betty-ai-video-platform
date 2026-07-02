"""
YouTube Source — Uses YouTube Data API v3 + optional yt-dlp for metadata enrichment.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.collector.sources.base import BaseSource, CollectResult
from app.collector.schemas import RawPost

logger = logging.getLogger(__name__)

# YouTube API quota cost per request
# search.list = 100 units, videos.list = 1 unit
# Daily quota: 10,000 units (default)


class YouTubeSource(BaseSource):
    """Collect trending content from YouTube."""

    source_name = "youtube"

    # Default search queries for viral content
    DEFAULT_QUERIES = [
        "viral video today",
        "trending now",
        "breaking news",
        "popular this week",
        "hot topics",
    ]

    # YouTube category IDs
    CATEGORIES = {
        "tech": "28",       # Science & Technology
        "gaming": "20",     # Gaming
        "music": "10",      # Music
        "entertainment": "24",  # Entertainment
        "news": "25",       # News & Politics
        "sports": "17",     # Sports
        "education": "27",  # Education
        "comedy": "23",     # Comedy
    }

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._api_key = os.getenv("YOUTUBE_API_KEY", "")
        self._quota_used = 0
        self._quota_limit = 10000
        if not self._api_key:
            logger.warning("[youtube] No YOUTUBE_API_KEY — using youtube-trending-scraper fallback")

    async def collect(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        region_code: str = "US",
        limit: int = 25,
        max_results: int = 50,
        order: str = "viewCount",  # viewCount | date | rating | relevance
        published_after: Optional[str] = None,  # ISO 8601
    ) -> CollectResult:
        """Collect trending videos from YouTube.

        Args:
            query: Search query. If None, uses mostPopular chart.
            category: Predefined category (tech/gaming/music/etc.)
            region_code: ISO 3166-1 alpha-2 country code
            limit: Max videos to return
            max_results: Max to fetch from API
            order: Sort order
            published_after: RFC 3339 timestamp
        """
        if not self._api_key:
            return await self._collect_fallback(query, limit)

        try:
            video_ids = await self._search_videos(query, category, region_code, max_results, order, published_after)
            if not video_ids:
                logger.info("[youtube] No videos found for query=%s", query)
                return CollectResult(source="youtube", posts=[])

            details = await self._get_video_details(video_ids[:limit])
            posts = [self._video_to_raw(v) for v in details]

            logger.info("[youtube] Collected %d videos (quota used: %d/%d)",
                        len(posts), self._quota_used, self._quota_limit)
            return CollectResult(
                source="youtube", posts=posts,
                rate_limit_remaining=self._quota_limit - self._quota_used,
            )
        except Exception as e:
            logger.exception("[youtube] Collection failed")
            return CollectResult(source="youtube", posts=[], error=str(e))

    async def _search_videos(
        self, query: Optional[str], category: Optional[str],
        region_code: str, max_results: int, order: str, published_after: Optional[str],
    ) -> list[str]:
        """Search YouTube and return video IDs."""
        import urllib.request
        import json
        from urllib.parse import urlencode

        loop = asyncio.get_event_loop()

        # Build search params
        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "type": "video",
            "maxResults": min(max_results, 50),
            "order": order,
            "regionCode": region_code,
            "relevanceLanguage": "en",
            "key": self._api_key,
        }

        if query:
            params["q"] = query
        else:
            # Use mostPopular chart if no query
            search_url = "https://www.googleapis.com/youtube/v3/videos"
            params["part"] = "snippet"
            params["chart"] = "mostPopular"
            params.pop("type", None)
            params.pop("q", None)
            params.pop("order", None)

        if category and category in self.CATEGORIES:
            params["videoCategoryId"] = self.CATEGORIES[category]

        if published_after:
            params["publishedAfter"] = published_after

        url = f"{search_url}?{urlencode(params)}"
        self._quota_used += 100  # search.list cost

        def _fetch():
            with urllib.request.urlopen(url, timeout=15) as resp:
                return json.loads(resp.read())

        try:
            data = await loop.run_in_executor(None, _fetch)
            items = data.get("items", [])
            return [item["id"]["videoId"] if "videoId" in item.get("id", {})
                    else item["id"] for item in items if item.get("id")]
        except Exception as e:
            logger.warning("[youtube] Search failed: %s", e)
            return []

    async def _get_video_details(self, video_ids: list[str]) -> list[dict]:
        """Get detailed info for videos (statistics + contentDetails)."""
        import urllib.request
        import json
        from urllib.parse import urlencode

        if not video_ids:
            return []

        loop = asyncio.get_event_loop()
        ids_str = ",".join(video_ids)
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": ids_str,
            "key": self._api_key,
        }
        url = f"https://www.googleapis.com/youtube/v3/videos?{urlencode(params)}"
        self._quota_used += 1  # videos.list cost (~1 unit per request)

        def _fetch():
            with urllib.request.urlopen(url, timeout=15) as resp:
                return json.loads(resp.read())

        try:
            data = await loop.run_in_executor(None, _fetch)
            return data.get("items", [])
        except Exception as e:
            logger.warning("[youtube] Video details failed: %s", e)
            return []

    async def _collect_fallback(self, query: Optional[str], limit: int) -> CollectResult:
        """Fallback: use youtube-trending-scraper or static trends."""
        try:
            import urllib.request
            import json

            loop = asyncio.get_event_loop()
            # Fallback to YouTube's oEmbed or RSS
            trending_url = "https://www.youtube.com/feed/trending"
            logger.info("[youtube] Falling back to trending page scrape")

            # Simple RSS approach for trending
            rss_url = "https://www.youtube.com/feeds/videos.xml"
            req = urllib.request.Request(rss_url, headers={"User-Agent": "betty/1.0"})

            def _fetch():
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read().decode()

            xml_data = await loop.run_in_executor(None, _fetch)

            # Parse RSS with regex (lightweight, no xml dep)
            import re
            entries = re.findall(r'<entry>(.*?)</entry>', xml_data, re.DOTALL)[:limit]
            posts = []
            for entry in entries:
                title_m = re.search(r'<title>(.*?)</title>', entry)
                link_m = re.search(r'<link.*?href=[\'"]([^\'"]+)[\'"]', entry)
                vid_id_m = re.search(r'video:([\w_-]+)', entry)
                author_m = re.search(r'<author>.*?<name>(.*?)</name>', entry, re.DOTALL)
                pub_m = re.search(r'<published>(.*?)</published>', entry)

                if title_m and link_m:
                    vid_id = vid_id_m.group(1) if vid_id_m else "unknown"
                    posts.append(RawPost(
                        source_platform="youtube",
                        source_id=f"yt_{vid_id}",
                        source_url=link_m.group(1),
                        title=title_m.group(1),
                        author=author_m.group(1) if author_m else None,
                        thumbnail_url=f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg" if vid_id != "unknown" else None,
                        source_created_at=datetime.fromisoformat(pub_m.group(1).replace("Z", "+00:00")) if pub_m else None,
                    ))

            return CollectResult(source="youtube", posts=posts)
        except Exception as e:
            logger.warning("[youtube] Fallback also failed: %s", e)
            return CollectResult(source="youtube", posts=[], error=str(e))

    def _video_to_raw(self, video: dict) -> RawPost:
        """Convert YouTube API video object to normalized RawPost."""
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})
        vid = video.get("id", "")

        published = None
        if snippet.get("publishedAt"):
            try:
                published = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        title = snippet.get("title", "")
        description = snippet.get("description", "")[:2000] if snippet.get("description") else None

        return RawPost(
            source_platform="youtube",
            source_id=f"yt_{vid}",
            source_url=f"https://www.youtube.com/watch?v={vid}",
            title=title,
            description=description,
            author=snippet.get("channelTitle"),
            channel=snippet.get("channelTitle"),
            thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url") or
                          snippet.get("thumbnails", {}).get("medium", {}).get("url"),
            category=snippet.get("categoryId"),
            upvotes=int(statistics.get("likeCount", 0)),
            comments=int(statistics.get("commentCount", 0)),
            shares=0,  # YouTube API doesn't expose share count
            views=int(statistics.get("viewCount", 0)),
            source_created_at=published,
            raw_data={
                "snippet": snippet,
                "statistics": statistics,
                "contentDetails": video.get("contentDetails", {}),
                "duration": video.get("contentDetails", {}).get("duration"),
                "tags": snippet.get("tags", []),
                "defaultLanguage": snippet.get("defaultAudioLanguage"),
            },
        )

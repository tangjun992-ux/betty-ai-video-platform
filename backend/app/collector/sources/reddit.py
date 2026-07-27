"""
Reddit Source — Uses PRAW (Python Reddit API Wrapper) or pushshift/reddit JSON API.
Falls back gracefully when credentials unavailable.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

from app.collector.sources.base import BaseSource, CollectResult
from app.collector.schemas import RawPost

logger = logging.getLogger(__name__)


class RedditSource(BaseSource):
    """Collect trending content from Reddit using PRAW or JSON API."""

    source_name = "reddit"

    # Default subreddits for viral content discovery
    DEFAULT_SUBREDDITS = [
        "videos", "Damnthatsinteresting", "nextfuckinglevel",
        "interestingasfuck", "oddlysatisfying", "Unexpected",
        "BeAmazed", "MadeMeSmile", "funny", "gifs",
        "technology", "gadgets", "science", "space",
        "todayilearned", "explainlikeimfive", "AskReddit",
    ]

    # Content categories mapped to subreddits
    CATEGORY_SUBREDDITS = {
        "tech": ["technology", "gadgets", "programming", "artificial", "MachineLearning"],
        "science": ["science", "space", "askscience", "Futurology"],
        "entertainment": ["videos", "funny", "gifs", "television", "movies"],
        "news": ["worldnews", "news", "politics", "TrueReddit"],
        "creative": ["Art", "Design", "photography", "CreativeCoding"],
        "gaming": ["gaming", "Games", "pcgaming", "NintendoSwitch"],
    }

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._praw = None
        self._praw_available = False
        self._init_praw()

    def _init_praw(self):
        """Try to init PRAW. Falls back to JSON API if unavailable."""
        try:
            import praw
            client_id = os.getenv("REDDIT_CLIENT_ID", "")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
            user_agent = os.getenv("REDDIT_USER_AGENT", "betty-viral-intel/1.0")

            if client_id and client_secret:
                self._praw = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent,
                    read_only=True,
                )
                self._praw_available = True
                logger.info("[reddit] PRAW initialized with API credentials")
            else:
                logger.warning("[reddit] No REDDIT_CLIENT_ID/SECRET — using JSON API fallback")
        except ImportError:
            logger.warning("[reddit] praw not installed — using JSON API fallback")
        except Exception as e:
            logger.warning("[reddit] PRAW init failed: %s — using JSON API", e)

    async def collect(
        self,
        subreddit: Optional[str] = None,
        subreddits: Optional[list[str]] = None,
        category: Optional[str] = None,
        limit: int = 25,
        time_filter: str = "day",
        sort: str = "hot",
    ) -> CollectResult:
        """Collect trending posts from Reddit.

        Args:
            subreddit: Single subreddit to scan
            subreddits: Multiple subreddits to scan
            category: Predefined category (tech/science/entertainment/news/creative/gaming)
            limit: Posts per subreddit
            time_filter: hour | day | week | month | year | all
            sort: hot | top | rising | new
        """
        target_subs = self._resolve_subreddits(subreddit, subreddits, category)
        all_posts: list[RawPost] = []

        for sub in target_subs:
            try:
                if self._praw_available:
                    posts = await self._collect_praw(sub, limit, time_filter, sort)
                else:
                    posts = await self._collect_json(sub, limit, time_filter, sort)
                all_posts.extend(posts)
            except Exception as e:
                logger.warning("[reddit] Subreddit %s failed: %s", sub, e)
                continue

        # Deduplicate by source_id
        seen = set()
        unique = []
        for p in all_posts:
            if p.source_id not in seen:
                seen.add(p.source_id)
                unique.append(p)

        logger.info("[reddit] Collected %d unique posts from %d subreddits", len(unique), len(target_subs))
        return CollectResult(source="reddit", posts=unique[:limit * len(target_subs)])

    async def _collect_praw(
        self, subreddit: str, limit: int, time_filter: str, sort: str,
    ) -> list[RawPost]:
        """Collect using PRAW (rate-limited by PRAW)."""
        loop = asyncio.get_event_loop()

        def _fetch():
            sub = self._praw.subreddit(subreddit)
            if sort == "top":
                submissions = sub.top(time_filter=time_filter, limit=limit)
            elif sort == "rising":
                submissions = sub.rising(limit=limit)
            elif sort == "new":
                submissions = sub.new(limit=limit)
            else:
                submissions = sub.hot(limit=limit)
            return list(submissions)

        submissions = await loop.run_in_executor(None, _fetch)
        return [self._praw_to_raw(s) for s in submissions]

    async def _collect_json(
        self, subreddit: str, limit: int, time_filter: str, sort: str,
    ) -> list[RawPost]:
        """Collect using Reddit JSON API (no auth needed)."""
        import urllib.request
        import json

        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}&t={time_filter}"
        req = urllib.request.Request(url, headers={"User-Agent": "betty-viral-intel/1.0"})

        loop = asyncio.get_event_loop()

        def _fetch():
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())

        try:
            data = await loop.run_in_executor(None, _fetch)
            children = data.get("data", {}).get("children", [])
            return [self._json_to_raw(c["data"]) for c in children if c.get("data")]
        except Exception as e:
            logger.warning("[reddit] JSON API failed for r/%s: %s", subreddit, e)
            return []

    def _praw_to_raw(self, submission) -> RawPost:
        """Convert PRAW submission to normalized RawPost."""
        created = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
        return RawPost(
            source_platform="reddit",
            source_id=f"reddit_{submission.id}",
            source_url=f"https://reddit.com{submission.permalink}",
            title=submission.title,
            description=submission.selftext[:2000] if submission.selftext else None,
            author=str(submission.author) if submission.author else None,
            thumbnail_url=submission.thumbnail if submission.thumbnail and submission.thumbnail.startswith("http") else None,
            subreddit=str(submission.subreddit),
            upvotes=submission.score,
            comments=submission.num_comments,
            shares=0,  # Reddit doesn't expose share count directly
            views=0,
            source_created_at=created,
            raw_data={
                "permalink": submission.permalink,
                "upvote_ratio": getattr(submission, "upvote_ratio", None),
                "is_original_content": getattr(submission, "is_original_content", False),
                "gilded": submission.gilded,
                "domain": getattr(submission, "domain", None),
                "link_flair_text": getattr(submission, "link_flair_text", None),
            },
        )

    def _json_to_raw(self, data: dict) -> RawPost:
        """Convert Reddit JSON API data to normalized RawPost."""
        created = datetime.fromtimestamp(data.get("created_utc", 0), tz=timezone.utc)
        thumbnail = data.get("thumbnail", "")
        return RawPost(
            source_platform="reddit",
            source_id=f"reddit_{data['id']}",
            source_url=f"https://reddit.com{data.get('permalink', '')}",
            title=data.get("title", ""),
            description=data.get("selftext", "")[:2000] if data.get("selftext") else None,
            author=data.get("author"),
            thumbnail_url=thumbnail if thumbnail.startswith("http") else None,
            subreddit=data.get("subreddit"),
            upvotes=data.get("score", 0),
            comments=data.get("num_comments", 0),
            shares=0,
            views=0,
            source_created_at=created,
            raw_data={
                "permalink": data.get("permalink"),
                "upvote_ratio": data.get("upvote_ratio"),
                "is_original_content": data.get("is_original_content", False),
                "gilded": data.get("gilded", 0),
                "domain": data.get("domain"),
                "link_flair_text": data.get("link_flair_text"),
            },
        )

    def _resolve_subreddits(
        self, subreddit: Optional[str], subreddits: Optional[list[str]], category: Optional[str],
    ) -> list[str]:
        """Resolve which subreddits to scan."""
        if subreddit:
            return [subreddit]
        if subreddits:
            return subreddits
        if category and category in self.CATEGORY_SUBREDDITS:
            return self.CATEGORY_SUBREDDITS[category]
        return self.DEFAULT_SUBREDDITS[:10]  # Limit to 10 to avoid rate issues

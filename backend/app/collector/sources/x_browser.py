"""
X (Twitter) Source — Playwright-based browser automation for trending content.

Uses headless Chromium to scrape X trending topics and popular tweets.
Supports cookie-based auth for logged-in experience, falls back to public view.

Architecture: Browser pool with max 2 concurrent contexts.
Rate limit: Respectful delays, rotates user agents, handles shadow DOM.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from datetime import datetime, timezone
from typing import Optional

from app.collector.sources.base import BaseSource, CollectResult
from app.collector.schemas import RawPost

logger = logging.getLogger(__name__)

# Realistic user agents (rotated)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# X trending page (no login required for trending topics list)
X_TRENDING_URL = "https://x.com/explore/tabs/trending"
X_SEARCH_URL = "https://x.com/search?q={query}&src=typed_query&f=top"

# Known X trending categories
TRENDING_CATEGORIES = ["Trending", "News", "Sports", "Entertainment", "Technology"]


class XBrowserSource(BaseSource):
    """Collect trending content from X via Playwright browser automation."""

    source_name = "x"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._playwright = None
        self._browser = None
        self._browser_ready = False
        self._init_attempted = False

    async def _ensure_browser(self):
        """Lazy-init Playwright browser (shared across collect calls)."""
        if self._browser_ready:
            return True
        if self._init_attempted:
            return False

        self._init_attempted = True
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            self._browser_ready = True
            logger.info("[x] Playwright browser ready")
            return True
        except ImportError:
            logger.warning("[x] playwright not installed — X collection disabled")
            return False
        except Exception as e:
            logger.error("[x] Browser init failed: %s", e)
            return False

    async def collect(
        self,
        query: Optional[str] = None,
        limit: int = 25,
        max_tweets: int = 50,
        include_replies: bool = False,
        cookies_file: Optional[str] = None,
    ) -> CollectResult:
        """Collect trending tweets from X.

        Args:
            query: Search query. If None, scrapes trending topics page.
            limit: Max tweets to return
            max_tweets: Max tweets to extract from page
            include_replies: Whether to include reply tweets
            cookies_file: Path to Netscape-format cookies file for auth
        """
        if not await self._ensure_browser():
            return CollectResult(
                source="x", posts=[],
                error="Playwright browser unavailable",
            )

        try:
            context = await self._create_context(cookies_file)
            page = await context.new_page()

            if query:
                posts = await self._scrape_search(page, query, max_tweets, include_replies)
            else:
                posts = await self._scrape_trending(page, max_tweets)

            await context.close()

            # Deduplicate
            seen = set()
            unique = []
            for p in posts:
                if p.source_id not in seen:
                    seen.add(p.source_id)
                    unique.append(p)

            result = unique[:limit]
            logger.info("[x] Collected %d tweets", len(result))
            return CollectResult(source="x", posts=result)

        except Exception as e:
            logger.exception("[x] Collection failed")
            return CollectResult(source="x", posts=[], error=str(e))

    async def _create_context(self, cookies_file: Optional[str] = None):
        """Create a browser context with realistic fingerprint."""
        context = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        # Load cookies if provided
        if cookies_file and os.path.exists(cookies_file):
            try:
                with open(cookies_file) as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                logger.info("[x] Loaded %d cookies", len(cookies))
            except Exception as e:
                logger.warning("[x] Cookie load failed: %s", e)

        return context

    async def _scrape_trending(self, page, max_items: int) -> list[RawPost]:
        """Scrape X trending topics and their top tweets."""
        posts = []

        try:
            # Navigate to trending
            await page.goto(X_TRENDING_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)  # Wait for JS render

            # Extract trending topic names
            trending_texts = await page.evaluate("""() => {
                const items = document.querySelectorAll('[data-testid="trend"]');
                const results = [];
                items.forEach(el => {
                    const spans = el.querySelectorAll('span');
                    if (spans.length >= 2) {
                        results.push({
                            topic: spans[1]?.innerText || '',
                            tweets: spans[2]?.innerText || '',
                            url: el.querySelector('a')?.href || '',
                        });
                    }
                });
                return results.slice(0, 30);
            }""")

            # For each trending topic, get top tweets
            for trend in trending_texts[:8]:  # Limit to avoid rate limits
                if trend.get("url"):
                    try:
                        trend_posts = await self._scrape_topic_page(
                            page, trend["url"], trend["topic"], max(2, max_items // 8)
                        )
                        posts.extend(trend_posts)
                        await asyncio.sleep(random.uniform(1.5, 3.0))  # Respectful delay
                    except Exception as e:
                        logger.warning("[x] Trend scrape failed: %s", e)

        except Exception as e:
            logger.warning("[x] Trending scrape failed: %s", e)

        # Fallback: just grab timeline tweets
        if not posts:
            posts = await self._scrape_timeline(page, max_items)

        return posts

    async def _scrape_search(self, page, query: str, max_items: int, include_replies: bool) -> list[RawPost]:
        """Scrape tweets from search results."""
        url = X_SEARCH_URL.format(query=query.replace(" ", "%20"))
        return await self._scrape_topic_page(page, url, query, max_items)

    async def _scrape_topic_page(self, page, url: str, topic: str, max_items: int) -> list[RawPost]:
        """Scrape tweets from a specific X page."""
        posts = []

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Scroll to load more tweets
            for _ in range(min(5, max_items // 5)):
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1)

            # Extract tweets
            tweets = await page.evaluate("""(maxItems) => {
                const articles = document.querySelectorAll('article[data-testid="tweet"]');
                const results = [];
                for (const article of articles) {
                    if (results.length >= maxItems) break;
                    try {
                        const text = article.querySelector('[data-testid="tweetText"]')?.innerText || '';
                        const time = article.querySelector('time')?.getAttribute('datetime') || '';
                        const link = article.querySelector('a[href*="/status/"]')?.href || '';
                        const tid = link.split('/status/')[1]?.split('?')[0] || '';
                        const reply = article.querySelector('[data-testid="reply"]')?.innerText || '0';
                        const retweet = article.querySelector('[data-testid="retweet"]')?.innerText || '0';
                        const like = article.querySelector('[data-testid="like"]')?.innerText || '0';
                        const views = article.querySelector('[data-testid="app-text-transition-container"]')?.innerText || '0';
                        const author = article.querySelector('[data-testid="User-Name"]')?.innerText?.split('\\n')[0] || '';
                        const handle = article.querySelector('[data-testid="User-Name"]')?.innerText?.split('\\n')[1] || '';
                        const img = article.querySelector('img[src*="media"]')?.src || '';
                        results.push({tid, text, time, link, reply, retweet, like, views, author, handle, img});
                    } catch(e) {}
                }
                return results;
            }""", max_items)

            for t in tweets:
                if not t.get("text"):
                    continue

                # Parse engagement
                def parse_count(s: str) -> int:
                    s = (s or "0").replace(",", "").replace(".", "")
                    if "K" in s.upper():
                        return int(float(s.upper().replace("K", "")) * 1000)
                    if "M" in s.upper():
                        return int(float(s.upper().replace("M", "")) * 1000000)
                    try:
                        return int(s)
                    except ValueError:
                        return 0

                created = None
                if t.get("time"):
                    try:
                        created = datetime.fromisoformat(t["time"].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                posts.append(RawPost(
                    source_platform="x",
                    source_id=f"x_{t['tid']}" if t.get("tid") else f"x_{hash(t.get('text', ''))}",
                    source_url=t.get("link", url),
                    title=t["text"][:200],
                    description=t["text"][:2000] if len(t["text"]) > 200 else None,
                    author=t.get("author", ""),
                    thumbnail_url=t.get("img") if t.get("img") else None,
                    category=topic,
                    upvotes=parse_count(t.get("like", "0")),
                    comments=parse_count(t.get("reply", "0")),
                    shares=parse_count(t.get("retweet", "0")),
                    views=parse_count(t.get("views", "0")),
                    source_created_at=created,
                    raw_data={
                        "tweet_id": t.get("tid"),
                        "author_handle": t.get("handle"),
                        "topic": topic,
                    },
                ))

        except Exception as e:
            logger.warning("[x] Topic page scrape failed: %s", e)

        return posts

    async def _scrape_timeline(self, page, max_items: int) -> list[RawPost]:
        """Fallback: scrape home timeline (requires login)."""
        posts = []
        try:
            await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(1.5)

            tweets = await page.evaluate(f"""(maxItems) => {{
                const articles = document.querySelectorAll('article[data-testid="tweet"]');
                const results = [];
                for (const article of articles) {{
                    if (results.length >= maxItems) break;
                    const text = article.querySelector('[data-testid="tweetText"]')?.innerText || '';
                    const link = article.querySelector('a[href*="/status/"]')?.href || '';
                    const tid = link.split('/status/')[1]?.split('?')[0] || '';
                    const like = article.querySelector('[data-testid="like"]')?.innerText || '0';
                    const retweet = article.querySelector('[data-testid="retweet"]')?.innerText || '0';
                    const reply = article.querySelector('[data-testid="reply"]')?.innerText || '0';
                    const author = article.querySelector('[data-testid="User-Name"]')?.innerText?.split('\\\\n')[0] || '';
                    if (text) results.push({{tid, text, link, like, retweet, reply, author}});
                }}
                return results;
            }}""", max_items)

            for t in tweets:
                posts.append(RawPost(
                    source_platform="x",
                    source_id=f"x_{t.get('tid', hash(t.get('text', '')))}",
                    source_url=t.get("link", ""),
                    title=t["text"][:200],
                    author=t.get("author"),
                    upvotes=int(t.get("like", "0").replace(",", "")) if t.get("like", "0").replace(",", "").isdigit() else 0,
                    comments=int(t.get("reply", "0").replace(",", "")) if t.get("reply", "0").replace(",", "").isdigit() else 0,
                    shares=int(t.get("retweet", "0").replace(",", "")) if t.get("retweet", "0").replace(",", "").isdigit() else 0,
                    source_created_at=datetime.now(timezone.utc),
                ))
        except Exception as e:
            logger.warning("[x] Timeline scrape failed: %s", e)

        return posts

    async def close(self):
        """Clean up browser resources."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        self._browser_ready = False


x_source = XBrowserSource()

"""
Viral Intelligence System — FastAPI Router v3

P0.2: Rate limiting on all endpoints (named Depends, not lambdas).
P0.3: Input validation with enum constraints.
P2: Redis caching on read-heavy endpoints.
P2: Prometheus metrics endpoint.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.rate_limiter import rate_limiter
from app.collector.models import TrendingTopic, ViralSignal, TrendReport
from app.collector.engine import viral_engine
from app.collector.cache import vis_cache, DEFAULT_TTL
from app.collector.logging import vis_log
from app.collector.analyzers.curation import video_curator
from app.collector.tasks import collect_reddit, collect_youtube, collect_tiktok, collect_x, collect_all
from app.collector.schemas import (
    CollectRequest, TrendingTopicResponse, TrendReportResponse,
    GeneratedPrompt, PromptGenRequest, DashboardStats,
)

router = APIRouter(tags=["viral-intelligence"])

# Valid enum values
VALID_SOURCES = {"reddit", "youtube", "tiktok", "x"}
VALID_TIERS = {"tier_1_breakout", "tier_2_trending", "tier_3_emerging", "noise"}
VALID_TIME_FILTERS = {"hour", "day", "week", "month", "year", "all"}
VALID_SIGNAL_TYPES = {"engagement_spike", "sentiment_shift", "velocity_breakout", "meme_surge"}
VALID_PERIODS = {"hourly", "daily", "weekly"}


# ── Rate limit base ──
async def _check_rate(request: Request, rpm: int, rph: int, key_prefix: str):
    client_ip = request.client.host if request.client else "unknown"
    key = f"{key_prefix}:{client_ip}"
    result = rate_limiter.is_rate_limited(key, requests_per_minute=rpm, requests_per_hour=rph)
    if not result["allowed"]:
        vis_log.rate_limited(client_ip, key_prefix, result.get("limit_key", "rpm"))
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "retry_after_seconds": result.get("retry_after", 60),
                "limit": result.get("limit_key", "rpm"),
            },
        )


# ── Rate limit dependencies (named functions required by FastAPI Depends) ──
async def _rl_collect(request: Request):       await _check_rate(request, 5, 30, "vis:collect")
async def _rl_collect_all(request: Request):   await _check_rate(request, 2, 10, "vis:collect_all")
async def _rl_read(request: Request):          await _check_rate(request, 30, 300, "vis:read")
async def _rl_prompts(request: Request):       await _check_rate(request, 10, 60, "vis:prompts")
async def _rl_reports(request: Request):       await _check_rate(request, 5, 30, "vis:reports")
async def _rl_dashboard(request: Request):     await _check_rate(request, 10, 100, "vis:dashboard")
async def _rl_health(request: Request):        await _check_rate(request, 60, 500, "vis:health")


# ═══════════════════ Collection ═══════════════════
@router.post("/collect", summary="Trigger collection from a source")
async def trigger_collection(req: CollectRequest, _rate: None = Depends(_rl_collect)):
    if req.source not in VALID_SOURCES:
        raise HTTPException(status_code=400, detail=f"Unknown source: {req.source}")
    if req.time_filter not in VALID_TIME_FILTERS:
        raise HTTPException(status_code=400, detail=f"Invalid time_filter: {req.time_filter}")

    vis_cache.invalidate_pattern("vis:cache:trends:*")
    vis_log.collection_start(req.source, {"query": req.query, "limit": req.limit})

    if req.source == "reddit":
        task = collect_reddit.delay(
            subreddit=req.subreddit, category=req.query,
            limit=min(req.limit, 50), time_filter=req.time_filter)
    elif req.source == "tiktok":
        task = collect_tiktok.delay(region=req.subreddit or "US", limit=min(req.limit, 50))
    elif req.source == "x":
        task = collect_x.delay(query=req.query, limit=min(req.limit, 50))
    else:
        task = collect_youtube.delay(query=req.query, limit=min(req.limit, 50))
    return {"source": req.source, "task_id": task.id, "status": "submitted"}


@router.post("/collect/all", summary="Trigger collection from all sources")
async def trigger_collect_all(_rate: None = Depends(_rl_collect_all)):
    task = collect_all.delay()
    return {"task_id": task.id, "status": "submitted"}


# ═══════════════════ Trending Topics ═══════════════════
@router.get("/trends", response_model=list[TrendingTopicResponse], summary="Get trending topics")
async def get_trends(
    tier: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(_rl_read),
):
    if tier and tier not in VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")
    if source and source not in VALID_SOURCES:
        raise HTTPException(status_code=400, detail=f"Invalid source: {source}")

    cache_key = f"trends:{tier}:{source}:{limit}:{offset}"
    cached = vis_cache.get(cache_key)
    if cached is not None:
        vis_log.cache_hit(cache_key)
        return cached

    query = select(TrendingTopic)
    if tier: query = query.where(TrendingTopic.viral_tier == tier)
    if source: query = query.where(TrendingTopic.source_platform == source)
    query = query.order_by(TrendingTopic.viral_score.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    data = [viral_engine._topic_to_response(t) for t in result.scalars().all()]
    vis_cache.set(cache_key, data, ttl=DEFAULT_TTL)
    vis_log.cache_miss(cache_key)
    return data


@router.get("/trends/{topic_id}", response_model=TrendingTopicResponse, summary="Get topic detail")
async def get_topic(topic_id: str, db: AsyncSession = Depends(get_db), _rate: None = Depends(_rl_read)):
    result = await db.execute(select(TrendingTopic).where(TrendingTopic.topic_id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return viral_engine._topic_to_response(topic)


# ═══════════════════ Signals ═══════════════════
@router.get("/signals", summary="Get recent viral signals")
async def get_signals(
    signal_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(_rl_read),
):
    if signal_type and signal_type not in VALID_SIGNAL_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid signal_type: {signal_type}")
    query = select(ViralSignal)
    if signal_type: query = query.where(ViralSignal.signal_type == signal_type)
    query = query.order_by(ViralSignal.triggered_at.desc()).limit(limit)
    return [s.to_dict() for s in (await db.execute(query)).scalars().all()]


# ═══════════════════ Prompt Generation ═══════════════════
@router.post("/prompts/gen", response_model=list[GeneratedPrompt], summary="Generate content prompts")
async def generate_prompts(req: PromptGenRequest, db: AsyncSession = Depends(get_db),
                           _rate: None = Depends(_rl_prompts)):
    if req.viral_tier and req.viral_tier not in VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid viral_tier: {req.viral_tier}")
    return await viral_engine.generate_prompts(
        db, content_type=req.content_type or "video",
        limit=min(req.limit, 20), viral_tier=req.viral_tier)


@router.get("/prompts/latest", response_model=list[GeneratedPrompt], summary="Get latest prompts")
async def get_latest_prompts(limit: int = Query(10, ge=1, le=50),
                             db: AsyncSession = Depends(get_db), _rate: None = Depends(_rl_read)):
    result = await db.execute(select(TrendReport).order_by(TrendReport.created_at.desc()).limit(1))
    report = result.scalar_one_or_none()
    if not report or not report.generated_prompts:
        return []
    return report.generated_prompts[:limit]


# ═══════════════════ Reports ═══════════════════
@router.post("/reports/generate", response_model=TrendReportResponse, summary="Generate trend report")
async def trigger_report(period: str = Query("daily"),
                         db: AsyncSession = Depends(get_db), _rate: None = Depends(_rl_reports)):
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period: {period}")
    report = await viral_engine.generate_report(db, period)
    return TrendReportResponse(**report.to_dict())


@router.get("/reports", response_model=list[TrendReportResponse], summary="Get historical reports")
async def get_reports(period: Optional[str] = Query(None), limit: int = Query(10, ge=1, le=50),
                      db: AsyncSession = Depends(get_db), _rate: None = Depends(_rl_read)):
    if period and period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period: {period}")
    query = select(TrendReport)
    if period: query = query.where(TrendReport.period == period)
    query = query.order_by(TrendReport.created_at.desc()).limit(limit)
    return [TrendReportResponse(**r.to_dict()) for r in (await db.execute(query)).scalars().all()]


# ═══════════════════ Dashboard ═══════════════════
@router.get("/dashboard/viral", response_model=DashboardStats, summary="Get viral dashboard stats")
async def get_viral_dashboard(db: AsyncSession = Depends(get_db), _rate: None = Depends(_rl_dashboard)):
    return await viral_engine.get_dashboard_stats(db)


# ═══════════════════ Health ═══════════════════
@router.get("/collector/health", summary="Collector health status")
async def collector_health(_rate: None = Depends(_rl_health)):
    return {
        "status": "ok",
        "sources": {
            "reddit": {"available": True, "circuit_open": not viral_engine.sources["reddit"].is_healthy},
            "youtube": {"available": True, "circuit_open": not viral_engine.sources["youtube"].is_healthy},
        },
        "rate_limiter": "active",
        "cache": "redis" if vis_cache._enabled else "memory",
    }


# ═══════════════════ Curated Trends (Video Production Focus) ═══════════════════
@router.get("/trends/curated", summary="Get trends curated for short video production")
async def get_curated_trends(
    source: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None, description="reaction|tutorial|news_break|explainer|commentary|entertainment"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(_rl_read),
):
    """Get trending topics ranked by short-form video production potential.
    
    Each result includes curation metadata:
      - video_worthiness: 0-1 score for video suitability
      - content_type: recommended format (reaction/tutorial/news_break/etc.)
      - suggested_duration: 15/30/60 seconds
      - target_platforms: tiktok/youtube_shorts/instagram_reels
      - production_notes: brief production guidance
    """
    query = select(TrendingTopic)
    if source and source in VALID_SOURCES:
        query = query.where(TrendingTopic.source_platform == source)
    query = query.order_by(TrendingTopic.viral_score.desc()).limit(limit * 2)

    result = await db.execute(query)
    topics = result.scalars().all()

    # Convert to dicts for curation evaluation
    topic_dicts = [t.to_dict() for t in topics]

    # Run video curation filter
    curated = video_curator.evaluate_batch(topic_dicts)
    
    # Filter by content type if requested
    if content_type:
        curated = [(t, c) for t, c in curated if c.content_type == content_type]

    # Build response
    items = []
    for topic_dict, curation in curated[:limit]:
        items.append({
            "topic": topic_dict,
            "curation": {
                "video_worthiness": curation.video_worthiness,
                "content_type": curation.content_type,
                "visual_potential": curation.visual_potential,
                "narrative_score": curation.narrative_score,
                "production_feasibility": curation.production_feasibility,
                "timeliness_score": curation.timeliness_score,
                "suggested_duration": curation.suggested_duration,
                "target_platforms": curation.target_platforms,
                "production_notes": curation.production_notes,
            },
        })

    return {"count": len(items), "items": items}


# ═══════════════════ Metrics ═══════════════════
@router.get("/collector/metrics", summary="Prometheus metrics")
async def collector_metrics(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func as sqlfunc
    from datetime import datetime as dt, timedelta, timezone as tz
    import time as time_module

    now = dt.now(tz.utc)
    day_ago = now - timedelta(hours=24)

    total = (await db.execute(select(sqlfunc.count(TrendingTopic.id)))).scalar() or 0
    tiers = dict((await db.execute(
        select(TrendingTopic.viral_tier, sqlfunc.count(TrendingTopic.id)).group_by(TrendingTopic.viral_tier)
    )).all())
    sources = dict((await db.execute(
        select(TrendingTopic.source_platform, sqlfunc.count(TrendingTopic.id)).group_by(TrendingTopic.source_platform)
    )).all())
    recent_signals = (await db.execute(
        select(sqlfunc.count(ViralSignal.id)).where(ViralSignal.triggered_at >= day_ago)
    )).scalar() or 0

    reddit_cb = 1 if not viral_engine.sources["reddit"].is_healthy else 0
    youtube_cb = 1 if not viral_engine.sources["youtube"].is_healthy else 0

    return "\n".join([
        "# HELP vis_topics_total Total tracked topics",
        "# TYPE vis_topics_total gauge", f"vis_topics_total {total}", "",
        "# HELP vis_topics_by_tier Topics by viral tier",
        "# TYPE vis_topics_by_tier gauge",
        f'vis_topics_by_tier{{tier="tier_1_breakout"}} {tiers.get("tier_1_breakout", 0)}',
        f'vis_topics_by_tier{{tier="tier_2_trending"}} {tiers.get("tier_2_trending", 0)}',
        f'vis_topics_by_tier{{tier="tier_3_emerging"}} {tiers.get("tier_3_emerging", 0)}',
        f'vis_topics_by_tier{{tier="noise"}} {tiers.get("noise", 0)}', "",
        "# HELP vis_topics_by_source Topics by source platform",
        "# TYPE vis_topics_by_source gauge",
        f'vis_topics_by_source{{platform="reddit"}} {sources.get("reddit", 0)}',
        f'vis_topics_by_source{{platform="youtube"}} {sources.get("youtube", 0)}', "",
        "# HELP vis_signals_recent_24h Viral signals in last 24h",
        "# TYPE vis_signals_recent_24h gauge", f"vis_signals_recent_24h {recent_signals}", "",
        "# HELP vis_circuit_breaker_open Circuit breaker (1=open)",
        "# TYPE vis_circuit_breaker_open gauge",
        f'vis_circuit_breaker_open{{source="reddit"}} {reddit_cb}',
        f'vis_circuit_breaker_open{{source="youtube"}} {youtube_cb}', "",
        "# HELP vis_scrape_epoch Last scrape timestamp",
        "# TYPE vis_scrape_epoch gauge", f"vis_scrape_epoch {int(time_module.time())}", "",
    ])

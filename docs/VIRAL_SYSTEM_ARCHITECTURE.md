"""
Betty Viral Intelligence System (VIS) — Architecture v1.0

Integration: Incremental module dentro Betty backend.
NOT a separate microservice. Reuses existing Redis/Celery/FastAPI/PostgreSQL.

## Architecture Layers

┌─────────────────────────────────────────────────────────┐
│  API Layer (FastAPI)                                     │
│  /api/v1/trends  /api/v1/signals  /api/v1/prompts/gen   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  Scheduler (Celery Beat + APScheduler)                   │
│  cron: Reddit 10m, YouTube 15m, TikTok 30m, X 20m       │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  Collector Layer (Sources)                               │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐     │
│  │ Reddit  │ │ YouTube  │ │ TikTok  │ │ X (Play) │     │
│  │ (PRAW)  │ │(API+yt)  │ │ (Apify) │ │ wright)  │     │
│  └────┬────┘ └────┬─────┘ └────┬────┘ └────┬─────┘     │
│       └───────────┴────────────┴───────────┘            │
│                    │ publish                            │
│                    ▼                                    │
│  ┌─────────────────────────────────────┐                │
│  │  Redis Streams                      │                │
│  │  collector:raw:posts                │                │
│  └──────────────────┬──────────────────┘                │
└─────────────────────┼──────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────┐
│  Analysis Pipeline (Celery Workers)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Viral    │ │ Growth   │ │Sentiment │ │ Hook     │  │
│  │ Score    │ │ Velocity │ │Analysis  │ │ Analysis │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│       └────────────┴────────────┴────────────┘          │
│                    │ union                              │
│                    ▼                                    │
│  ┌─────────────────────────────────────┐                │
│  │  Redis Stream: analyzer:results     │                │
│  └──────────────────┬──────────────────┘                │
└─────────────────────┼──────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────┐
│  Prompt Generator + Director Integration                │
│  trend → viral_context → Director.brief → content       │
└─────────────────────────────────────────────────────────┘

## Data Flow (Redis Streams)

Stream: collector:reddit (consumer group: analyzers)
  ┌─ Worker-1: viral_score_calc
  ├─ Worker-2: sentiment_analyze
  ├─ Worker-3: growth_track (reads from DB)
  └─ Worker-4: hook_extract

Consumer Group pattern: each analyzer is a separate consumer in the same group.
Auto-ack after processing. Dead letter queue for failures.

## DB Schema (New tables in existing DB)

trending_topics:
  - id (PK), topic_id (UUID), source_platform, source_id
  - title, description, url, thumbnail_url
  - engagement: {upvotes, comments, shares, views}
  - growth_metrics: {velocity_1h, velocity_6h, velocity_24h, acceleration}
  - viral_signals: {score, tier, breakout_probability}
  - sentiment: {positive, negative, neutral, controversy_index}
  - hooks: [{pattern, strength, category}]
  - meme_matches: [{template, confidence}]
  - raw_data (JSON), analyzed_at, created_at, updated_at

viral_signals:
  - id (PK), signal_id (UUID), topic_id (FK)
  - signal_type: engagement_spike | sentiment_shift | velocity_breakout | meme_surge
  - confidence, evidence (JSON)
  - triggered_at

trend_reports:
  - id (PK), report_id (UUID), period (hourly/daily/weekly)
  - summary, top_topics (JSON), category_distribution, platform_distribution
  - generated_prompts (JSON), created_at

## Viral Score Algorithm

V = w1·E_norm + w2·G_norm + w3·S_norm + w4·N_norm + w5·M_norm

Where:
  E_norm = normalized engagement (views+upvotes+comments+shares) / max_in_window
  G_norm  = growth_velocity / max_velocity_in_window
  S_norm  = (positive_ratio - negative_ratio) clamped to [0,1]  → polarity strength
  N_norm  = 1 - cosine_similarity(topic, historical_topics)  → novelty
  M_norm  = meme_match_strength (0-1)

Weights (configurable):
  w1(engagement)=0.30, w2(growth)=0.30, w3(sentiment)=0.15, w4(novelty)=0.15, w5(meme)=0.10

Tiers:
  V ≥ 0.80 → TIER_1 (BREAKOUT)     → immediate alert + prompt gen
  V ≥ 0.60 → TIER_2 (TRENDING)     → monitor + report
  V ≥ 0.40 → TIER_3 (EMERGING)     → track only
  V < 0.40 → NOISE

## Growth Velocity

Vel(t) = (E(t) - E(t-Δt)) / Δt  where Δt∈{1h, 6h, 24h}
Acceleration = d²E/dt² ≈ (Vel(t) - Vel(t-Δt)) / Δt

Breakout detection:
  IF Vel_1h > μ_vel + 2.5σ AND acceleration > 0 THEN "BREAKOUT"

## Hook Analysis (13 hook patterns)
1. Curiosity Gap    — "You won't believe..."
2. Controversy      — Polarizing statement
3. Pattern Interrupt— Unexpected visual/audio
4. Social Proof     — "X million people..."
5. Scarcity/Urgency — "Only 24 hours..."
6. Story Hook       — "Last week I..."  
7. Question Hook    — Starts with question
8. Statistic Hook   — "87% of people..."
9. Before/After     — Transformation
10. Challenge       — "Can you..."
11. Listicle        — "5 reasons why..."
12. Relatability     — "Me every morning..."
13. Authority        — Expert/celebrity claim

Detection: LLM-classify + regex patterns + structural cues (first 3s text, caption, title)

## Rate Limiting (per-source token buckets)

  Reddit:    60 req/min (PRAW default)
  YouTube:   10,000 units/day (quota system)
  TikTok:    Apify actor concurrency limit
  X:         Playwright browser pool (max 3 concurrent)

Implementation: Redis-backed sliding window + token bucket per source.
Circuit breaker: 5 consecutive failures → 5min cooldown.

## Deployment (add to existing docker-compose)

New services:
  - celery-collector (new queue: collector_q, concurrency=2)
  - celery-analyzer  (new queue: analyzer_q, concurrency=4)

Existing services (unchanged):
  - api, celery-worker, celery-beat, redis, db, flower, frontend

## Agent Integration (future)

VIS exposes a tool interface for Director:
  director_context = vis.get_trending_context(category="tech", limit=5)
  # returns: [{topic, viral_score, hook_patterns, suggested_angles}]
  brief = f"Make a video about {topic} using hook: {best_hook}"
  -> Director.plan(brief) -> content production

## Resilience

- Each source wrapped in try/except → NodeResult(success=True)+fallback
- Rate limit exhaustion → graceful degradation (skip source, log warning)
- Source API down → circuit breaker → stale cache (Redis TTL 1h)
- Analysis failure → retry 3x → dead letter stream for manual review
- Full pipeline monitoring via Celery Flower + Prometheus metrics
"""
print("ARCHITECTURE DOCUMENTED")

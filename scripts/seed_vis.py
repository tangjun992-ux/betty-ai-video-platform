#!/usr/bin/env python3
"""Seed the VIS database with sample trending data for dashboard demo."""
import sys, os, json, uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/home/tom/ai-video-platform/backend")

import asyncio
from app.db import async_session
from app.collector.models import TrendingTopic, ViralSignal

SAMPLE_TOPICS = [
    {
        "source_platform": "reddit", "source_id": "seed_1",
        "title": "OpenAI quietly drops GPT-5 preview in API — developers report 10x reasoning improvement",
        "description": "Multiple developers noticed a new model endpoint. Benchmarks show significant gains on MATH and HumanEval.",
        "author": "u/ml_researcher", "subreddit": "MachineLearning",
        "engagement_upvotes": 45200, "engagement_comments": 3200, "engagement_shares": 8900, "engagement_views": 890000,
        "growth_velocity_1h": 1250, "growth_velocity_6h": 8900, "growth_velocity_24h": 45000,
        "growth_acceleration": 320, "engagement_score": 42100,
        "viral_score": 0.92, "viral_tier": "tier_1_breakout", "breakout_probability": 0.88,
        "sentiment_positive": 0.72, "sentiment_negative": 0.08, "sentiment_neutral": 0.20, "sentiment_controversy": 0.15,
        "hooks": [
            {"category": "curiosity_gap", "pattern": "Curiosity Gap", "strength": 0.92, "matched_text": "OpenAI quietly drops GPT-5 preview"},
            {"category": "social_proof", "pattern": "Social Proof", "strength": 0.78, "matched_text": "10x reasoning improvement"},
        ],
        "meme_matches": [
            {"template": "Galaxy Brain", "category": "image_macro", "confidence": 0.65},
        ],
    },
    {
        "source_platform": "youtube", "source_id": "seed_2",
        "title": "I built an AI that plays Elden Ring better than me — here's how",
        "description": "Used reinforcement learning and computer vision. The AI discovered strategies no human speedrunner uses.",
        "author": "CodeBullet", "channel": "CodeBullet",
        "engagement_upvotes": 289000, "engagement_comments": 15600, "engagement_shares": 45000, "engagement_views": 3400000,
        "growth_velocity_1h": 8500, "growth_velocity_6h": 120000, "growth_velocity_24h": 890000,
        "growth_acceleration": 2100, "engagement_score": 320000,
        "viral_score": 0.95, "viral_tier": "tier_1_breakout", "breakout_probability": 0.94,
        "sentiment_positive": 0.88, "sentiment_negative": 0.02, "sentiment_neutral": 0.10, "sentiment_controversy": 0.05,
        "hooks": [
            {"category": "story_hook", "pattern": "Story Hook", "strength": 0.88, "matched_text": "I built an AI that plays Elden Ring"},
            {"category": "challenge", "pattern": "Challenge", "strength": 0.72, "matched_text": "better than me"},
        ],
        "meme_matches": [],
    },
    {
        "source_platform": "reddit", "source_id": "seed_3",
        "title": "TIL: Python 3.14 will include a built-in JIT compiler — 2-5x speedup for pure Python",
        "description": "PEP accepted. The copy-and-patch JIT compiles hot loops at runtime with zero config.",
        "author": "u/pythonista", "subreddit": "programming",
        "engagement_upvotes": 124000, "engagement_comments": 8900, "engagement_shares": 23000, "engagement_views": 2100000,
        "growth_velocity_1h": 3400, "growth_velocity_6h": 28000, "growth_velocity_24h": 124000,
        "growth_acceleration": 580, "engagement_score": 128000,
        "viral_score": 0.88, "viral_tier": "tier_1_breakout", "breakout_probability": 0.82,
        "sentiment_positive": 0.82, "sentiment_negative": 0.05, "sentiment_neutral": 0.13, "sentiment_controversy": 0.10,
        "hooks": [
            {"category": "statistic_hook", "pattern": "Statistic Hook", "strength": 0.85, "matched_text": "2-5x speedup"},
            {"category": "curiosity_gap", "pattern": "Curiosity Gap", "strength": 0.68, "matched_text": "TIL"},
        ],
        "meme_matches": [
            {"template": "Stonks", "category": "image_macro", "confidence": 0.55},
        ],
    },
    {
        "source_platform": "tiktok", "source_id": "seed_4",
        "title": "POV: You're a junior dev who just discovered ChatGPT can write your unit tests",
        "description": "#programming #devlife #chatgpt #coding",
        "author": "@techbro99",
        "engagement_upvotes": 890000, "engagement_comments": 45000, "engagement_shares": 120000, "engagement_views": 8200000,
        "growth_velocity_1h": 25000, "growth_velocity_6h": 350000, "growth_velocity_24h": 2100000,
        "growth_acceleration": 8200, "engagement_score": 950000,
        "viral_score": 0.97, "viral_tier": "tier_1_breakout", "breakout_probability": 0.96,
        "sentiment_positive": 0.78, "sentiment_negative": 0.06, "sentiment_neutral": 0.16, "sentiment_controversy": 0.20,
        "hooks": [
            {"category": "curiosity_gap", "pattern": "Curiosity Gap", "strength": 0.91, "matched_text": "POV: You're a junior dev"},
            {"category": "relatability", "pattern": "Relatability", "strength": 0.85, "matched_text": "just discovered ChatGPT"},
        ],
        "meme_matches": [
            {"template": "POV Format", "category": "tiktok_caption", "confidence": 0.92},
            {"template": "Surprised Pikachu", "category": "image_macro", "confidence": 0.72},
        ],
    },
    {
        "source_platform": "x", "source_id": "seed_5",
        "title": "Nobody:\nAbsolutely nobody:\nElon Musk: I'm buying OpenAI for $97 billion and turning it into a pizza chain",
        "author": "@dril",
        "engagement_upvotes": 670000, "engagement_comments": 89000, "engagement_shares": 230000, "engagement_views": 15000000,
        "growth_velocity_1h": 45000, "growth_velocity_6h": 670000, "growth_velocity_24h": 3400000,
        "growth_acceleration": 15000, "engagement_score": 720000,
        "viral_score": 0.99, "viral_tier": "tier_1_breakout", "breakout_probability": 0.98,
        "sentiment_positive": 0.45, "sentiment_negative": 0.30, "sentiment_neutral": 0.25, "sentiment_controversy": 0.72,
        "hooks": [
            {"category": "controversy", "pattern": "Controversy", "strength": 0.95, "matched_text": "Elon Musk"},
            {"category": "pattern_interrupt", "pattern": "Pattern Interrupt", "strength": 0.88, "matched_text": "pizza chain"},
        ],
        "meme_matches": [
            {"template": "Nobody: Abs. Nobody:", "category": "format", "confidence": 0.95},
            {"template": "Wojak Universe", "category": "wojak", "confidence": 0.68},
        ],
    },
    {
        "source_platform": "reddit", "source_id": "seed_6",
        "title": "We analyzed 10 million YouTube thumbnails — here's what actually drives clicks",
        "description": "Face ratio > 30%, red color, and surprised expressions correlate most with CTR. Full data in comments.",
        "author": "u/dataisbeautiful", "subreddit": "dataisbeautiful",
        "engagement_upvotes": 89000, "engagement_comments": 5600, "engagement_shares": 15000, "engagement_views": 1600000,
        "growth_velocity_1h": 2200, "growth_velocity_6h": 18000, "growth_velocity_24h": 89000,
        "growth_acceleration": 340, "engagement_score": 92000, "category": "tech",
        "viral_score": 0.82, "viral_tier": "tier_1_breakout", "breakout_probability": 0.72,
        "sentiment_positive": 0.68, "sentiment_negative": 0.08, "sentiment_neutral": 0.24, "sentiment_controversy": 0.08,
        "hooks": [
            {"category": "statistic_hook", "pattern": "Statistic Hook", "strength": 0.90, "matched_text": "10 million YouTube thumbnails"},
            {"category": "curiosity_gap", "pattern": "Curiosity Gap", "strength": 0.76, "matched_text": "what actually drives clicks"},
        ],
        "meme_matches": [],
    },
    {
        "source_platform": "youtube", "source_id": "seed_7",
        "title": "Apple Vision Pro 2 leaks — lighter, cheaper, and actually useful this time?",
        "author": "MKBHD", "channel": "MKBHD",
        "engagement_upvotes": 450000, "engagement_comments": 28000, "engagement_shares": 67000, "engagement_views": 5200000,
        "growth_velocity_1h": 12000, "growth_velocity_6h": 180000, "growth_velocity_24h": 890000,
        "growth_acceleration": 2800, "engagement_score": 480000, "category": "tech",
        "viral_score": 0.86, "viral_tier": "tier_1_breakout", "breakout_probability": 0.78,
        "sentiment_positive": 0.55, "sentiment_negative": 0.22, "sentiment_neutral": 0.23, "sentiment_controversy": 0.35,
        "hooks": [
            {"category": "question_hook", "pattern": "Question Hook", "strength": 0.82, "matched_text": "actually useful this time?"},
            {"category": "scarcity_urgency", "pattern": "Scarcity/Urgency", "strength": 0.65, "matched_text": "leaks"},
        ],
        "meme_matches": [
            {"template": "This Is Fine", "category": "image_macro", "confidence": 0.58},
        ],
    },
    {
        "source_platform": "reddit", "source_id": "seed_8",
        "title": "5 things every developer should stop doing in 2026",
        "author": "u/senior_dev", "subreddit": "programming",
        "engagement_upvotes": 34000, "engagement_comments": 4200, "engagement_shares": 8900, "engagement_views": 780000,
        "growth_velocity_1h": 890, "growth_velocity_6h": 12000, "growth_velocity_24h": 34000,
        "growth_acceleration": 120, "engagement_score": 36000, "category": "tech",
        "viral_score": 0.72, "viral_tier": "tier_2_trending", "breakout_probability": 0.55,
        "sentiment_positive": 0.35, "sentiment_negative": 0.42, "sentiment_neutral": 0.23, "sentiment_controversy": 0.48,
        "hooks": [
            {"category": "listicle", "pattern": "Listicle", "strength": 0.92, "matched_text": "5 things every developer"},
            {"category": "controversy", "pattern": "Controversy", "strength": 0.72, "matched_text": "should stop doing"},
        ],
        "meme_matches": [],
    },
    {
        "source_platform": "x", "source_id": "seed_9",
        "title": "hot take: typescript is just javascript with extra steps and we're all pretending it's revolutionary",
        "author": "@hot_takes_dev",
        "engagement_upvotes": 230000, "engagement_comments": 34000, "engagement_shares": 56000, "engagement_views": 4500000,
        "growth_velocity_1h": 8900, "growth_velocity_6h": 120000, "growth_velocity_24h": 560000,
        "growth_acceleration": 1200, "engagement_score": 245000, "category": "tech",
        "viral_score": 0.84, "viral_tier": "tier_1_breakout", "breakout_probability": 0.74,
        "sentiment_positive": 0.35, "sentiment_negative": 0.48, "sentiment_neutral": 0.17, "sentiment_controversy": 0.68,
        "hooks": [
            {"category": "controversy", "pattern": "Controversy", "strength": 0.93, "matched_text": "hot take"},
        ],
        "meme_matches": [
            {"template": "Virgin vs Chad", "category": "comparison", "confidence": 0.72},
            {"template": "Change My Mind", "category": "image_macro", "confidence": 0.78},
        ],
    },
    {
        "source_platform": "tiktok", "source_id": "seed_10",
        "title": "When you finally understand recursion after 3 years of programming",
        "description": "#coding #programming #recursion #relatable",
        "author": "@dev_memes",
        "engagement_upvotes": 560000, "engagement_comments": 23000, "engagement_shares": 78000, "engagement_views": 6100000,
        "growth_velocity_1h": 18000, "growth_velocity_6h": 250000, "growth_velocity_24h": 1200000,
        "growth_acceleration": 4500, "engagement_score": 590000, "category": "tech",
        "viral_score": 0.90, "viral_tier": "tier_1_breakout", "breakout_probability": 0.85,
        "sentiment_positive": 0.85, "sentiment_negative": 0.02, "sentiment_neutral": 0.13, "sentiment_controversy": 0.05,
        "hooks": [
            {"category": "relatability", "pattern": "Relatability", "strength": 0.92, "matched_text": "When you finally understand"},
            {"category": "story_hook", "pattern": "Story Hook", "strength": 0.68, "matched_text": "3 years of programming"},
        ],
        "meme_matches": [
            {"template": "When You... Format", "category": "tiktok_caption", "confidence": 0.88},
            {"template": "Doge", "category": "image_macro", "confidence": 0.55},
        ],
    },
    # Emerging tier
    {
        "source_platform": "reddit", "source_id": "seed_e1",
        "title": "New research: LLMs can now self-correct mathematical errors without human feedback",
        "author": "u/ai_papers", "subreddit": "artificial",
        "engagement_upvotes": 12000, "engagement_comments": 890, "engagement_shares": 2300, "engagement_views": 280000,
        "growth_velocity_1h": 320, "growth_velocity_6h": 2800, "growth_velocity_24h": 12000,
        "growth_acceleration": 45, "engagement_score": 12800, "category": "tech",
        "viral_score": 0.58, "viral_tier": "tier_3_emerging", "breakout_probability": 0.32,
        "sentiment_positive": 0.78, "sentiment_negative": 0.03, "sentiment_neutral": 0.19, "sentiment_controversy": 0.05,
        "hooks": [{"category": "curiosity_gap", "pattern": "Curiosity Gap", "strength": 0.72, "matched_text": "new research"}],
        "meme_matches": [],
    },
    {
        "source_platform": "youtube", "source_id": "seed_e2",
        "title": "Why I switched from VS Code to Neovim (and you should too)",
        "author": "ThePrimeagen", "channel": "ThePrimeagen",
        "engagement_upvotes": 8900, "engagement_comments": 1200, "engagement_shares": 2100, "engagement_views": 180000,
        "growth_velocity_1h": 340, "growth_velocity_6h": 4500, "growth_velocity_24h": 8900,
        "growth_acceleration": 28, "engagement_score": 9500, "category": "tech",
        "viral_score": 0.52, "viral_tier": "tier_3_emerging", "breakout_probability": 0.22,
        "sentiment_positive": 0.42, "sentiment_negative": 0.38, "sentiment_neutral": 0.20, "sentiment_controversy": 0.55,
        "hooks": [{"category": "authority", "pattern": "Authority", "strength": 0.75, "matched_text": "Why I switched"}],
        "meme_matches": [{"template": "Gigachad", "category": "image_macro", "confidence": 0.68}],
    },
]

async def seed():
    now = datetime.now(timezone.utc)
    async with async_session() as db:
        for i, t in enumerate(SAMPLE_TOPICS):
            # Stagger timestamps
            created = now - timedelta(hours=len(SAMPLE_TOPICS) - i)

            topic = TrendingTopic(
                topic_id=f"seed_{t['source_id']}",
                source_platform=t["source_platform"],
                source_id=t["source_id"],
                source_url=f"https://{t['source_platform']}.com/seed/{t['source_id']}",
                title=t["title"],
                description=t.get("description"),
                author=t.get("author"),
                subreddit=t.get("subreddit"),
                channel=t.get("channel"),
                category=t.get("category"),
                engagement_upvotes=t["engagement_upvotes"],
                engagement_comments=t["engagement_comments"],
                engagement_shares=t["engagement_shares"],
                engagement_views=t["engagement_views"],
                engagement_score=t["engagement_score"],
                growth_velocity_1h=t["growth_velocity_1h"],
                growth_velocity_6h=t["growth_velocity_6h"],
                growth_velocity_24h=t["growth_velocity_24h"],
                growth_acceleration=t["growth_acceleration"],
                viral_score=t["viral_score"],
                viral_tier=t["viral_tier"],
                breakout_probability=t["breakout_probability"],
                sentiment_positive=t["sentiment_positive"],
                sentiment_negative=t["sentiment_negative"],
                sentiment_neutral=t["sentiment_neutral"],
                sentiment_controversy=t["sentiment_controversy"],
                hooks_detected=t.get("hooks", []),
                meme_matches=t.get("meme_matches", []),
                source_created_at=created,
                first_seen_at=created,
                last_analyzed_at=now,
                raw_data={"seed": True},
            )
            db.add(topic)

            # Add signal for breakouts
            if t["viral_tier"] in ("tier_1_breakout", "tier_2_trending"):
                db.add(ViralSignal(
                    topic_id=f"seed_{t['source_id']}",
                    signal_type="velocity_breakout" if t.get("breakout_probability", 0) > 0.7 else "engagement_spike",
                    confidence=t.get("breakout_probability", t["viral_score"]),
                    evidence={"score": t["viral_score"], "tier": t["viral_tier"]},
                ))

        await db.commit()
        print(f"✅ Seeded {len(SAMPLE_TOPICS)} topics ({sum(1 for t in SAMPLE_TOPICS if t['viral_tier']=='tier_1_breakout')} breakouts, {sum(1 for t in SAMPLE_TOPICS if t['viral_tier']=='tier_2_trending')} trending, {sum(1 for t in SAMPLE_TOPICS if t['viral_tier']=='tier_3_emerging')} emerging)")

asyncio.run(seed())

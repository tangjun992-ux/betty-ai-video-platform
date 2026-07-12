"""
Seed the explore gallery with a rich, curated showcase so /explore mirrors the
density and polish of yapper.so/explore even before real users generate content.

All media is rendered locally by the demo provider (Pillow + ffmpeg) and stored
under STORAGE_LOCAL_PATH, so it is stable and never expires. Safe to re-run:
existing demo-seed rows are cleared first (matched by the marker in parameters).

Usage:
    cd backend && source .venv/bin/activate && \
        STORAGE_PATH=/tmp/aivideo-media python scripts/seed_gallery.py
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.adapters.demo_provider import render_demo_image, render_demo_video

SEED_MARKER = "demo_seed_v1"

# (prompt, media_type, style, model, resolution, duration, likes, views)
SPECS = [
    ("赛博朋克风格的未来都市夜景，霓虹灯与飞行汽车，电影感光效", "image", "cyberpunk", "nano-banana-2", "1080x1920", 0, 342, 5210),
    ("A hyper-realistic portrait of a young woman, soft studio lighting, 85mm", "image", "portrait", "gpt-image-2", "1024x1024", 0, 511, 8830),
    ("宁静的雪山日出，云海翻涌，电影级广角风光大片", "video", "cinematic", "seedance-2.0", "1920x1080", 6, 288, 4120),
    ("可爱的橘猫宇航员漂浮在太空中，卡通渲染，明亮色彩", "image", "cute/kawaii", "nano-banana-2", "1024x1024", 0, 623, 9910),
    ("高端腕表产品摄影，深色背景，反光金属质感，商业广告级", "image", "product", "gpt-image-2", "1024x1024", 0, 197, 3050),
    ("日式庭院中的樱花飘落，唯美动漫风格，柔和粉色调", "image", "anime", "nano-banana-2", "1080x1920", 0, 734, 12030),
    ("A cinematic sci-fi spaceship interior, volumetric lighting, ultra detailed", "image", "sci-fi", "gpt-image-2", "1920x1080", 0, 405, 6720),
    ("电影感的城市街头，雨夜霓虹倒影，赛博朋克氛围，慢镜头", "video", "cyberpunk", "seedance-2.0-fast", "1080x1920", 5, 512, 8200),
    ("梦幻森林中的魔法精灵，奇幻艺术风格，发光粒子", "image", "fantasy", "nano-banana-2", "1024x1024", 0, 289, 4560),
    ("美食摄影：热气腾腾的日式拉面，暖色调，浅景深特写", "image", "food", "gpt-image-2", "1024x1024", 0, 356, 5890),
    ("现代极简主义建筑，混凝土与玻璃，蓝天白云，广角建筑摄影", "image", "architecture", "gpt-image-2", "1920x1080", 0, 178, 2940),
    ("抽象艺术画作，流动的油彩，明亮的撞色，当代艺术", "image", "artistic", "nano-banana-2", "1024x1024", 0, 245, 3780),
    ("超现实主义场景：漂浮的岛屿与倒置的瀑布，梦境般的天空", "image", "surreal", "gpt-image-2", "1080x1920", 0, 467, 7120),
    ("3D 渲染的可爱机器人角色，柔和材质，工作室灯光，皮克斯风格", "image", "3d-render", "nano-banana-2", "1024x1024", 0, 601, 9340),
    ("壮丽的挪威峡湾风光，极光在夜空舞动，长曝光风景大片", "video", "landscape", "seedance-2.0", "1920x1080", 6, 398, 6010),
    ("时尚杂志封面人像，戏剧性侧光，高级感妆容，写实质感", "image", "portrait", "gpt-image-2", "1080x1920", 0, 289, 4890),
    ("卡通风格的城市天际线，扁平插画，明快配色，社交媒体banner", "image", "cartoon", "nano-banana-2", "1920x1080", 0, 156, 2340),
    ("科幻机甲战士，金属反光，蓝色能量光效，电影级细节", "image", "sci-fi", "gpt-image-2", "1080x1920", 0, 712, 11200),
    ("A cozy coffee shop interior, warm morning light, lifestyle photography", "image", "realistic", "gpt-image-2", "1920x1080", 0, 203, 3410),
    ("动感的滑板运动瞬间，城市涂鸦墙背景，高速快门抓拍", "video", "energetic", "seedance-2.0-fast", "1080x1920", 5, 334, 5230),
    ("治愈系插画：小女孩与巨大的猫咪坐在星空下，温暖故事感", "image", "storytelling", "nano-banana-2", "1024x1024", 0, 588, 8760),
    ("纪录片风格的非洲草原日落，剪影动物群，自然光", "image", "documentary", "gpt-image-2", "1920x1080", 0, 267, 4180),
    ("可爱的柴犬表情包，夸张呆萌表情，白色背景，meme 风格", "image", "meme", "nano-banana-2", "1024x1024", 0, 891, 15400),
    ("未来科技感的产品发布会舞台，全息投影，冷色调灯光", "video", "sci-fi", "seedance-2.0", "1920x1080", 6, 421, 6890),
    ("水下世界的珊瑚礁，五彩斑斓的热带鱼，光线穿透海面", "image", "landscape", "gpt-image-2", "1024x1024", 0, 312, 4970),
    ("赛博格少女半身肖像，全息元素，霓虹紫粉，科幻人像", "image", "portrait", "nano-banana-2", "1080x1920", 0, 654, 10300),
    ("温馨的圣诞场景，壁炉与礼物，暖色灯光，节日氛围插画", "image", "cute/kawaii", "nano-banana-2", "1024x1024", 0, 423, 6540),
    ("电影级汽车广告镜头，跑车在盘山公路飞驰，黄昏光影", "video", "cinematic", "seedance-2.0", "1920x1080", 6, 545, 8910),
    ("奇幻风格的漂浮城堡，云端之上，金色阳光，史诗级场景", "image", "fantasy", "gpt-image-2", "1920x1080", 0, 478, 7450),
    ("极简主义的产品海报，几何构图，柔和渐变背景，高端排版", "image", "product", "nano-banana-2", "1080x1920", 0, 189, 2870),
    ("动漫风格的校园场景，夏日午后，蓝天白云，青春氛围", "image", "anime", "nano-banana-2", "1920x1080", 0, 767, 11900),
    ("搞笑的猫咪弹钢琴，拟人化插画，鲜艳色彩，幽默风格", "image", "funny", "nano-banana-2", "1024x1024", 0, 445, 6980),
]


def _sync_db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if url.startswith("sqlite+aiosqlite"):
        url = url.replace("sqlite+aiosqlite", "sqlite")
    elif url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql")
    return url


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    engine = create_engine(_sync_db_url())
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        # Clear previous demo-seed rows so re-running stays idempotent.
        rows = session.execute(text("SELECT id, parameters FROM tasks")).fetchall()
        to_delete = []
        for rid, params in rows:
            try:
                p = json.loads(params) if isinstance(params, str) else (params or {})
            except Exception:
                p = {}
            if isinstance(p, dict) and p.get("seed_marker") == SEED_MARKER:
                to_delete.append(rid)
        if to_delete:
            session.execute(
                text("DELETE FROM tasks WHERE id IN :ids").bindparams(
                    __import__("sqlalchemy").bindparam("ids", expanding=True)
                ),
                {"ids": to_delete},
            )
            session.commit()
            print(f"Cleared {len(to_delete)} previous demo-seed rows")

        created = 0
        for i, (prompt, media, style, model, res, dur, likes, views) in enumerate(SPECS):
            try:
                if media == "video":
                    url, thumb = render_demo_video(prompt, res, dur or 5, style)
                    results = [{
                        "type": "video", "url": url, "thumbnail": thumb,
                        "model": model, "resolution": res, "duration": dur, "cost": 3.0,
                    }]
                    cost = 3.0 * max(1, (dur or 5) // 5)
                else:
                    url = render_demo_image(prompt, res, style, index=0)
                    results = [{
                        "type": "image", "url": url, "thumbnail": url,
                        "model": model, "resolution": res, "cost": 2.0,
                    }]
                    cost = 2.0
            except Exception as e:
                print(f"  ! skip [{i}] {prompt[:30]}… render failed: {e}")
                continue

            ts = now - timedelta(hours=i * 3, minutes=(i * 17) % 60)
            params = {
                "resolution": res,
                "duration": dur if media == "video" else None,
                "count": 1,
                "style": style,
                "routing_info": json.dumps({"detected_styles": [style]}),
                "seed_marker": SEED_MARKER,
            }
            session.execute(
                text("""
                    INSERT INTO tasks
                    (task_id, user_id, prompt, media_type, quality, requested_model,
                     selected_model, parameters, status, progress, current_stage,
                     started_at, completed_at, estimated_cost, actual_cost, results,
                     created_at, updated_at)
                    VALUES
                    (:task_id, 0, :prompt, :media_type, 'high', 'auto',
                     :model, :params, 'completed', 100, 'completed',
                     :ts, :ts, :cost, :cost, :results, :ts, :ts)
                """),
                {
                    "task_id": str(uuid.uuid4()),
                    "prompt": prompt,
                    "media_type": media,
                    "model": model,
                    "params": json.dumps(params),
                    "ts": ts,
                    "cost": cost,
                    "results": json.dumps(results),
                },
            )
            created += 1
            print(f"  + [{created}/{len(SPECS)}] {media:5s} {style:12s} {prompt[:36]}")
        session.commit()
        print(f"\nSeeded {created} gallery items.")


if __name__ == "__main__":
    main()

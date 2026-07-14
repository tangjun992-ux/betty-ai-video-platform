"""
Pricing plans API — subscription tiers and credits bundles.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models.user import User
from app.models.billing import UserBalance

router = APIRouter()


class PlanFeature(BaseModel):
    name: str
    included: bool


class PricingPlan(BaseModel):
    id: str  # starter | personal | creator | pro
    name: str
    monthly_price: float
    yearly_price: float
    credits_per_month: int
    features: list[PlanFeature]
    highlighted: bool = False
    badge: Optional[str] = None


PLANS: list[PricingPlan] = [
    PricingPlan(
        id="starter",
        name="入门版",
        monthly_price=9.99,
        yearly_price=7.99,
        credits_per_month=1000,
        features=[
            PlanFeature(name="Seedance 2.0 全模态视频", included=False),
            PlanFeature(name="16+ 专业图片模型", included=True),
            PlanFeature(name="23+ 专业视频模型", included=False),
            PlanFeature(name="高级唇形同步", included=True),
            PlanFeature(name="高级图片编辑器", included=True),
            PlanFeature(name="视频 & 图片放大", included=True),
            PlanFeature(name="高级运动控制", included=True),
            PlanFeature(name="商用授权许可", included=False),
            PlanFeature(name="团队协作", included=False),
            PlanFeature(name="优先支持", included=False),
        ],
    ),
    PricingPlan(
        id="personal",
        name="个人版",
        monthly_price=24.99,
        yearly_price=19.99,
        credits_per_month=3000,
        features=[
            PlanFeature(name="Seedance 2.0 全模态视频", included=True),
            PlanFeature(name="16+ 专业图片模型", included=True),
            PlanFeature(name="23+ 专业视频模型", included=True),
            PlanFeature(name="高级唇形同步", included=True),
            PlanFeature(name="高级图片编辑器", included=True),
            PlanFeature(name="视频 & 图片放大", included=True),
            PlanFeature(name="高级运动控制", included=True),
            PlanFeature(name="商用授权许可", included=False),
            PlanFeature(name="团队协作", included=False),
            PlanFeature(name="优先支持", included=False),
        ],
    ),
    PricingPlan(
        id="creator",
        name="创作者版",
        monthly_price=49.99,
        yearly_price=39.99,
        credits_per_month=7000,
        highlighted=True,
        badge="最受欢迎 🔥",
        features=[
            PlanFeature(name="Seedance 2.0 全模态视频", included=True),
            PlanFeature(name="16+ 专业图片模型", included=True),
            PlanFeature(name="23+ 专业视频模型", included=True),
            PlanFeature(name="高级唇形同步", included=True),
            PlanFeature(name="高级图片编辑器", included=True),
            PlanFeature(name="视频 & 图片放大", included=True),
            PlanFeature(name="高级运动控制", included=True),
            PlanFeature(name="商用授权许可", included=True),
            PlanFeature(name="团队协作", included=True),
            PlanFeature(name="优先支持", included=True),
        ],
    ),
    PricingPlan(
        id="pro",
        name="专业版",
        monthly_price=99.99,
        yearly_price=79.99,
        credits_per_month=15000,
        features=[
            PlanFeature(name="Seedance 2.0 全模态视频", included=True),
            PlanFeature(name="16+ 专业图片模型", included=True),
            PlanFeature(name="23+ 专业视频模型", included=True),
            PlanFeature(name="高级唇形同步", included=True),
            PlanFeature(name="高级图片编辑器", included=True),
            PlanFeature(name="视频 & 图片放大", included=True),
            PlanFeature(name="高级运动控制", included=True),
            PlanFeature(name="商用授权许可", included=True),
            PlanFeature(name="团队协作", included=True),
            PlanFeature(name="优先支持", included=True),
        ],
    ),
]


@router.get("/plans", summary="获取所有定价方案")
async def get_pricing_plans(cycle: str = "monthly"):
    """Return all available subscription plans. cycle: 'monthly' or 'yearly'"""
    result = []
    for plan in PLANS:
        price = plan.yearly_price if cycle == "yearly" else plan.monthly_price
        result.append({
            "id": plan.id,
            "name": plan.name,
            "price": price,
            "credits_per_month": plan.credits_per_month,
            "cycle": cycle,
            "features": [f.model_dump() for f in plan.features],
            "highlighted": plan.highlighted,
            "badge": plan.badge,
        })
    return {"plans": result, "cycle": cycle}


@router.get("/user", summary="获取当前用户余额信息")
async def get_user_balance(user_id: int = 0, db: AsyncSession = Depends(get_db)):
    """Get the current user's balance and usage stats."""
    balance = None
    user = None

    try:
        result = await db.execute(select(UserBalance).where(UserBalance.user_id == user_id))
        balance = result.scalar_one_or_none()

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
    except Exception:
        pass

    if balance is None:
        return {
            "user_id": user_id,
            "credits": 0,
            "total_spent": 0,
            "total_tasks": 0,
            "role": "free",
        }

    return {
        "user_id": user_id,
        "credits": balance.credits + balance.daily_credits,
        "purchased_credits": balance.credits,
        "daily_credits": balance.daily_credits,
        "daily_credits_max": balance.daily_credits_max,
        "total_spent": balance.total_spent,
        "total_tasks": balance.total_tasks,
        "total_purchased": balance.total_purchased,
        "role": user.role if user else "free",
    }


@router.post("/subscribe", summary="订阅方案（模拟）")
async def subscribe(plan_id: str, user_id: int = 0, db: AsyncSession = Depends(get_db)):
    """Simulate subscribing to a plan — adds credits to user balance (dev only)."""
    from app.config import settings
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")
    plan = next((p for p in PLANS if p.id == plan_id), None)
    if not plan:
        return {"error": f"Plan '{plan_id}' not found"}, 404

    # Get or create balance
    result = await db.execute(select(UserBalance).where(UserBalance.user_id == user_id))
    balance = result.scalar_one_or_none()

    if balance is None:
        balance = UserBalance(user_id=user_id, credits=0)
        db.add(balance)

    balance.credits += plan.credits_per_month
    balance.total_purchased += plan.credits_per_month

    await db.flush()

    return {
        "success": True,
        "plan": plan.name,
        "credits_added": plan.credits_per_month,
        "new_balance": balance.credits + balance.daily_credits,
    }


@router.get("/costs", summary="费用统计")
async def get_cost_stats(days: int = 30):
    """Return cost statistics: total, by-model, by-type, recent history."""
    import sqlite3, os, json
    from datetime import datetime, timedelta, timezone

    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", db_path)
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
    else:
        return {"error": "Cost stats only available with SQLite backend"}, 501

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Total costs
    cur.execute("""
        SELECT COUNT(*) as total_tasks,
               COALESCE(SUM(estimated_cost), 0) as total_estimated,
               COALESCE(SUM(actual_cost), 0) as total_actual
        FROM tasks WHERE created_at >= ?
    """, (cutoff,))
    totals = cur.fetchone()
    total_tasks, total_est, total_act = totals

    # By model
    cur.execute("""
        SELECT selected_model,
               COUNT(*) as count,
               COALESCE(AVG(actual_cost), 0) as avg_cost,
               COALESCE(SUM(actual_cost), 0) as total_cost
        FROM tasks
        WHERE created_at >= ? AND status = 'completed'
        GROUP BY selected_model
        ORDER BY total_cost DESC
    """, (cutoff,))
    by_model = [
        {"model": r[0], "count": r[1], "avg_cost": round(r[2], 2), "total_cost": round(r[3], 2)}
        for r in cur.fetchall()
    ]

    # By media type
    cur.execute("""
        SELECT media_type,
               COUNT(*) as count,
               COALESCE(SUM(actual_cost), 0) as total_cost
        FROM tasks
        WHERE created_at >= ? AND status = 'completed'
        GROUP BY media_type
    """, (cutoff,))
    by_type = [
        {"type": r[0], "count": r[1], "total_cost": round(r[2], 2)}
        for r in cur.fetchall()
    ]

    # Daily breakdown
    cur.execute("""
        SELECT DATE(created_at) as day,
               COUNT(*) as count,
               COALESCE(SUM(actual_cost), 0) as total_cost,
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as succeeded,
               SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
        FROM tasks
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY day DESC
    """, (cutoff,))
    daily = [
        {"day": r[0], "count": r[1], "total_cost": round(r[2], 2),
         "succeeded": r[3], "failed": r[4]}
        for r in cur.fetchall()
    ]

    # Recent tasks with cost
    cur.execute("""
        SELECT task_id, media_type, selected_model, estimated_cost, actual_cost,
               status, created_at
        FROM tasks
        WHERE created_at >= ?
        ORDER BY created_at DESC
        LIMIT 50
    """, (cutoff,))
    recent = [
        {
            "task_id": r[0], "type": r[1], "model": r[2],
            "estimated_cost": r[3], "actual_cost": r[4],
            "status": r[5], "created_at": r[6],
        }
        for r in cur.fetchall()
    ]

    conn.close()

    return {
        "period_days": days,
        "summary": {
            "total_tasks": total_tasks,
            "total_estimated_cost": round(total_est, 2),
            "total_actual_cost": round(total_act, 2),
        },
        "by_model": by_model,
        "by_type": by_type,
        "daily": daily,
        "recent": recent,
    }

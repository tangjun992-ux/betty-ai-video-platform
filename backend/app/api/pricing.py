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
            PlanFeature(name="17+ 专业图片模型", included=True),
            PlanFeature(name="24+ 专业视频模型", included=False),
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
            PlanFeature(name="17+ 专业图片模型", included=True),
            PlanFeature(name="24+ 专业视频模型", included=True),
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
            PlanFeature(name="17+ 专业图片模型", included=True),
            PlanFeature(name="24+ 专业视频模型", included=True),
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
        name="Max",
        monthly_price=149.99,
        yearly_price=119.99,
        credits_per_month=22500,
        badge="最佳价值",
        features=[
            PlanFeature(name="Seedance 2.0 全模态视频", included=True),
            PlanFeature(name="17+ 专业图片模型", included=True),
            PlanFeature(name="24+ 专业视频模型", included=True),
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


def _plan_days_remaining(plan_started_at, plan_cycle: Optional[str]) -> Optional[int]:
    """Days remaining in the current billing cycle, given when the plan started.
    Returns None when there is no active plan; clamps to [0, cycle_days]."""
    if not plan_started_at:
        return None
    from datetime import datetime, timezone
    cycle_days = 365 if plan_cycle == "yearly" else 30
    started = plan_started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - started).days
    return max(0, min(cycle_days, cycle_days - elapsed))


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
            "current_plan_id": None,
            "plan_cycle": None,
            "plan_days_remaining": None,
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
        "current_plan_id": balance.current_plan_id,
        "plan_cycle": balance.plan_cycle,
        "plan_days_remaining": _plan_days_remaining(balance.plan_started_at, balance.plan_cycle),
    }


@router.post("/subscribe", summary="订阅方案（模拟）")
async def subscribe(plan_id: str, user_id: int = 0, db: AsyncSession = Depends(get_db)):
    """Simulate subscribing to a plan — adds credits to user balance."""
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


def compute_proration(current_plan_id: Optional[str], new_plan_id: str,
                      days_remaining: int, cycle_days: int = 30,
                      cycle: str = "monthly") -> dict:
    """Compute a mid-cycle plan change on a strict proration basis (对齐前端
    "随时按比例调整方案" 承诺)。

    The user is credited for the unused portion of their current plan and charged
    the prorated cost of the new plan for the days remaining in the cycle. Credits
    are granted proportionally to the remaining days too. Returns a breakdown with
    the net charge (may be a credit/refund when downgrading).
    """
    cycle_days = max(1, cycle_days)
    days_remaining = max(0, min(days_remaining, cycle_days))
    frac = days_remaining / cycle_days  # fraction of cycle left

    new_plan = next((p for p in PLANS if p.id == new_plan_id), None)
    if not new_plan:
        raise ValueError(f"Plan '{new_plan_id}' not found")
    cur_plan = next((p for p in PLANS if p.id == current_plan_id), None) if current_plan_id else None

    def _price(p) -> float:
        return p.yearly_price if cycle == "yearly" else p.monthly_price

    new_price = _price(new_plan)
    cur_price = _price(cur_plan) if cur_plan else 0.0

    # Unused value of the current plan credited back, prorated by remaining days.
    unused_credit = round(cur_price * frac, 2)
    # Cost of the new plan for the remainder of the cycle.
    new_prorated = round(new_price * frac, 2)
    net_charge = round(new_prorated - unused_credit, 2)

    # Credits granted for the prorated remainder of the new plan.
    prorated_credits = int(round(new_plan.credits_per_month * frac))

    return {
        "current_plan": current_plan_id,
        "new_plan": new_plan_id,
        "cycle": cycle,
        "cycle_days": cycle_days,
        "days_remaining": days_remaining,
        "proration_factor": round(frac, 4),
        "unused_credit_usd": unused_credit,
        "new_plan_prorated_usd": new_prorated,
        "net_charge_usd": net_charge,
        "is_refund": net_charge < 0,
        "prorated_credits": prorated_credits,
    }


@router.get("/proration-preview", summary="方案变更按比例预览（升/降级）")
async def proration_preview(new_plan_id: str, current_plan_id: Optional[str] = None,
                            days_remaining: int = 30, cycle: str = "monthly"):
    """Preview the prorated net charge and credits for switching to ``new_plan_id``
    mid-cycle. Makes the "随时按比例调整方案" promise concrete and verifiable."""
    cycle_days = 365 if cycle == "yearly" else 30
    try:
        return compute_proration(current_plan_id, new_plan_id, days_remaining,
                                 cycle_days=cycle_days, cycle=cycle)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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

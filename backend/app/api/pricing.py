"""
Pricing plans API — subscription tiers and credits bundles.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.auth import resolve_user_id
from app.models.user import User
from app.models.billing import UserBalance

router = APIRouter()


class PlanFeature(BaseModel):
    name: str
    included: bool


class PricingPlan(BaseModel):
    id: str  # starter | personal | creator | max  (pro kept as alias of max)
    name: str
    monthly_price: float
    yearly_price: float
    credits_per_month: int
    features: list[PlanFeature]
    highlighted: bool = False
    badge: Optional[str] = None
    # Optional credit tiers for Max slider (Yapper parity)
    credit_tiers: Optional[list[int]] = None


def normalize_plan_id(plan_id: str) -> str:
    """Map legacy `pro` → `max` (Yapper naming)."""
    pid = (plan_id or "").strip().lower()
    if pid == "pro":
        return "max"
    return pid


PLANS: list[PricingPlan] = [
    PricingPlan(
        id="starter",
        name="入门版",
        monthly_price=9.99,
        yearly_price=7.99,
        credits_per_month=1000,
        features=[
            PlanFeature(name="Seedance 2.0 全模态视频", included=False),
            PlanFeature(name="已验证图片模型（含 Imagen / GPT Image）", included=True),
            PlanFeature(name="已验证视频模型（Seedance / Kling）", included=False),
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
            PlanFeature(name="已验证图片模型（含 Imagen / GPT Image）", included=True),
            PlanFeature(name="已验证视频模型（Seedance / Kling）", included=True),
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
            PlanFeature(name="已验证图片模型（含 Imagen / GPT Image）", included=True),
            PlanFeature(name="已验证视频模型（Seedance / Kling）", included=True),
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
        id="max",
        name="Max",
        monthly_price=149.99,
        yearly_price=119.99,
        credits_per_month=22500,
        badge="Best Value",
        credit_tiers=[15000, 22500, 37000, 75000, 150000],
        features=[
            PlanFeature(name="Seedance 2.0 Omni 全模态视频", included=True),
            PlanFeature(name="已验证图片模型（含 Imagen / GPT Image）", included=True),
            PlanFeature(name="已验证视频模型（Seedance / Kling）", included=True),
            PlanFeature(name="高级唇形同步", included=True),
            PlanFeature(name="高级图片编辑器", included=True),
            PlanFeature(name="视频 & 图片放大", included=True),
            PlanFeature(name="高级运动控制", included=True),
            PlanFeature(name="商用授权许可", included=True),
            PlanFeature(name="团队协作", included=True),
            PlanFeature(name="优先支持 / Express Support", included=True),
        ],
    ),
]


def get_plan(plan_id: str) -> Optional[PricingPlan]:
    pid = normalize_plan_id(plan_id)
    return next((p for p in PLANS if p.id == pid), None)


@router.get("/plans", summary="获取所有定价方案")
async def get_pricing_plans(cycle: str = "monthly"):
    """Return all available subscription plans. cycle: 'monthly' or 'yearly'"""
    result = []
    for plan in PLANS:
        price = plan.yearly_price if cycle == "yearly" else plan.monthly_price
        row = {
            "id": plan.id,
            "name": plan.name,
            "price": price,
            "monthly_price": plan.monthly_price,
            "yearly_price": plan.yearly_price,
            "credits_per_month": plan.credits_per_month,
            "cycle": cycle,
            "features": [f.model_dump() for f in plan.features],
            "highlighted": plan.highlighted,
            "badge": plan.badge,
        }
        if plan.credit_tiers:
            row["credit_tiers"] = plan.credit_tiers
        if plan.id == "max":
            row["aliases"] = ["pro"]  # backward compat
        result.append(row)
    return {"plans": result, "cycle": cycle}


@router.get("/user", summary="获取当前用户余额信息")
async def get_user_balance(user_id: int = Depends(resolve_user_id), db: AsyncSession = Depends(get_db)):
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
async def subscribe(plan_id: str, user_id: int = Depends(resolve_user_id), db: AsyncSession = Depends(get_db)):
    """Simulate subscribing to a plan — adds credits to user balance (dev only)."""
    from app.config import settings
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")
    plan = get_plan(plan_id)
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

    # Image tools: charged credits (estimated) vs upstream burn (actual/res.cost)
    cur.execute("""
        SELECT COUNT(*) as n,
               COALESCE(SUM(estimated_cost), 0) as charged,
               COALESCE(SUM(actual_cost), 0) as upstream
        FROM tasks
        WHERE created_at >= ? AND media_type = 'image_tool'
    """, (cutoff,))
    tool_row = cur.fetchone()
    tool_n, tool_charged, tool_upstream = tool_row or (0, 0, 0)

    cur.execute("""
        SELECT selected_model,
               COUNT(*) as count,
               COALESCE(SUM(estimated_cost), 0) as charged,
               COALESCE(SUM(actual_cost), 0) as upstream
        FROM tasks
        WHERE created_at >= ? AND media_type = 'image_tool' AND status = 'completed'
        GROUP BY selected_model
        ORDER BY charged DESC
    """, (cutoff,))
    tools_by_model = [
        {
            "model": r[0], "count": r[1],
            "charged_credits": round(r[2], 2),
            "upstream_cost": round(r[3], 2),
            "margin_credits": round(r[2] - r[3], 2),
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
        "tools": {
            "count": int(tool_n or 0),
            "charged_credits": round(float(tool_charged or 0), 2),
            "upstream_cost": round(float(tool_upstream or 0), 2),
            "margin_credits": round(float(tool_charged or 0) - float(tool_upstream or 0), 2),
            "by_model": tools_by_model,
            "note": "charged_credits=平台预扣；upstream_cost=适配器 res.cost（KIE 上报）",
        },
        "charged_vs_upstream": {
            "charged_credits": round(float(total_est or 0), 2),
            "upstream_cost": round(float(total_act or 0), 2),
            "margin_credits": round(float(total_est or 0) - float(total_act or 0), 2),
        },
    }

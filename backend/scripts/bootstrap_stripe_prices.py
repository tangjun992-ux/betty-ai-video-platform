#!/usr/bin/env python3
"""Create Stripe Products/Prices for Betty plans and emit env lines.

Usage:
  # Dry plan (no API calls) — always safe in CI
  python scripts/bootstrap_stripe_prices.py --dry-run

  # Real create (requires STRIPE_API_KEY; prefer sk_test_*)
  STRIPE_API_KEY=sk_test_... python scripts/bootstrap_stripe_prices.py

  # Append to .env (never commits secrets; review before deploy)
  STRIPE_API_KEY=sk_test_... python scripts/bootstrap_stripe_prices.py --write-env .env

Idempotent: looks up existing products by metadata betty_plan_id + betty_cycle.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Plan catalog aligned with app.api.pricing.PLANS amounts (USD).
PLAN_PRICES = [
    ("starter", "monthly", 9.0, "STRIPE_PRICE_STARTER_MONTHLY"),
    ("starter", "yearly", 90.0, "STRIPE_PRICE_STARTER_YEARLY"),
    ("personal", "monthly", 19.0, "STRIPE_PRICE_PERSONAL_MONTHLY"),
    ("personal", "yearly", 190.0, "STRIPE_PRICE_PERSONAL_YEARLY"),
    ("creator", "monthly", 29.0, "STRIPE_PRICE_CREATOR_MONTHLY"),
    ("creator", "yearly", 290.0, "STRIPE_PRICE_CREATOR_YEARLY"),
    ("pro", "monthly", 79.0, "STRIPE_PRICE_PRO_MONTHLY"),
    ("pro", "yearly", 790.0, "STRIPE_PRICE_PRO_YEARLY"),
]
SEAT = ("team_seat", "monthly", 9.99, "STRIPE_PRICE_TEAM_SEAT_MONTHLY")


def _plan_amounts_from_catalog() -> list[tuple[str, str, float, str]]:
    try:
        from app.api.pricing import PLANS
        out = []
        env_map = {
            ("starter", "monthly"): "STRIPE_PRICE_STARTER_MONTHLY",
            ("starter", "yearly"): "STRIPE_PRICE_STARTER_YEARLY",
            ("personal", "monthly"): "STRIPE_PRICE_PERSONAL_MONTHLY",
            ("personal", "yearly"): "STRIPE_PRICE_PERSONAL_YEARLY",
            ("creator", "monthly"): "STRIPE_PRICE_CREATOR_MONTHLY",
            ("creator", "yearly"): "STRIPE_PRICE_CREATOR_YEARLY",
            ("pro", "monthly"): "STRIPE_PRICE_PRO_MONTHLY",
            ("pro", "yearly"): "STRIPE_PRICE_PRO_YEARLY",
        }
        for p in PLANS:
            # yearly_price in catalog is discounted *monthly* rate; Stripe yearly
            # Price charges once per year → amount = yearly_price * 12.
            out.append((p.id, "monthly", float(p.monthly_price), env_map[(p.id, "monthly")]))
            out.append(
                (p.id, "yearly", round(float(p.yearly_price) * 12, 2), env_map[(p.id, "yearly")])
            )
        return out
    except Exception:
        return list(PLAN_PRICES)


def dry_plan() -> dict[str, Any]:
    rows = _plan_amounts_from_catalog() + [SEAT]
    return {
        "mode": "dry-run",
        "note": "No Stripe API calls. Set STRIPE_API_KEY and omit --dry-run to create.",
        "items": [
            {
                "plan": plan,
                "cycle": cycle,
                "unit_amount_usd": amount,
                "env": env_key,
                "interval": "month" if cycle == "monthly" else "year",
            }
            for plan, cycle, amount, env_key in rows
        ],
    }


def _find_or_create_product(stripe, plan_id: str, name: str) -> str:
    # Search active products with matching metadata
    products = stripe.Product.list(limit=100, active=True)
    for p in products.auto_paging_iter():
        meta = getattr(p, "metadata", None) or {}
        if meta.get("betty_plan_id") == plan_id:
            return p.id
    prod = stripe.Product.create(
        name=name,
        metadata={"betty_plan_id": plan_id, "betty": "1"},
    )
    return prod.id


def _find_or_create_price(
    stripe, *, product_id: str, plan_id: str, cycle: str, amount_usd: float,
) -> str:
    interval = "month" if cycle == "monthly" else "year"
    unit = int(round(amount_usd * 100))
    prices = stripe.Price.list(product=product_id, active=True, limit=100)
    for pr in prices.auto_paging_iter():
        meta = getattr(pr, "metadata", None) or {}
        if meta.get("betty_plan_id") == plan_id and meta.get("betty_cycle") == cycle:
            return pr.id
        # Match by amount+interval if metadata missing
        if (
            getattr(pr, "unit_amount", None) == unit
            and getattr(pr, "recurring", None)
            and pr.recurring.get("interval") == interval
        ):
            return pr.id
    price = stripe.Price.create(
        product=product_id,
        unit_amount=unit,
        currency="usd",
        recurring={"interval": interval},
        metadata={"betty_plan_id": plan_id, "betty_cycle": cycle, "betty": "1"},
    )
    return price.id


def create_prices() -> dict[str, Any]:
    key = (os.getenv("STRIPE_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("STRIPE_API_KEY not set")
    import stripe

    stripe.api_key = key
    env_lines: dict[str, str] = {}
    details = []
    for plan, cycle, amount, env_key in _plan_amounts_from_catalog():
        product_id = _find_or_create_product(stripe, plan, f"betty · {plan}")
        price_id = _find_or_create_price(
            stripe, product_id=product_id, plan_id=plan, cycle=cycle, amount_usd=amount,
        )
        env_lines[env_key] = price_id
        details.append({"env": env_key, "price_id": price_id, "product_id": product_id})

    seat_plan, seat_cycle, seat_amt, seat_env = SEAT
    seat_prod = _find_or_create_product(stripe, seat_plan, "betty · team seat")
    seat_price = _find_or_create_price(
        stripe, product_id=seat_prod, plan_id=seat_plan, cycle=seat_cycle, amount_usd=seat_amt,
    )
    env_lines[seat_env] = seat_price
    details.append({"env": seat_env, "price_id": seat_price, "product_id": seat_prod})

    return {"mode": "live", "env": env_lines, "details": details}


def write_env(path: str, env_lines: dict[str, str]) -> None:
    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = f.read()
    lines = existing.splitlines()
    keys = set(env_lines)
    kept = [ln for ln in lines if not any(ln.startswith(f"{k}=") for k in keys)]
    kept.append("")
    kept.append("# Betty Stripe Price IDs (bootstrap_stripe_prices.py)")
    for k, v in env_lines.items():
        kept.append(f"{k}={v}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(kept).rstrip() + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Stripe Prices for Betty")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without API calls")
    parser.add_argument("--json-only", action="store_true", help="Emit only JSON (no env stub lines)")
    parser.add_argument("--write-env", metavar="PATH", help="Append/update Price IDs into env file")
    args = parser.parse_args()

    if args.dry_run or not (os.getenv("STRIPE_API_KEY") or "").strip():
        report = dry_plan()
        if not args.dry_run and not (os.getenv("STRIPE_API_KEY") or "").strip():
            report["note"] = "STRIPE_API_KEY unset — dry plan only. No prices created."
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not args.json_only:
            for item in report["items"]:
                print(
                    f"# {item['env']}=price_xxx  "
                    f"# {item['plan']} {item['cycle']} ${item['unit_amount_usd']}"
                )
        return 0

    try:
        report = create_prices()
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.json_only:
        for k, v in report["env"].items():
            print(f"{k}={v}")
    if args.write_env:
        write_env(args.write_env, report["env"])
        print(f"# wrote {args.write_env}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

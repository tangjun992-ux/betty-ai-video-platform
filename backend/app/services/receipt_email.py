"""
Receipt email stub — logs receipt payload; optionally sends via SMTP when
SMTP_HOST / SMTP_FROM are configured. No heavy email SDK dependencies.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Optional

logger = logging.getLogger(__name__)


def send_receipt_email(
    *,
    to_email: Optional[str] = None,
    order_no: str,
    label: str,
    credits: int,
    amount_usd: float,
    provider: str = "",
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Best-effort receipt delivery. Always logs; SMTP send is optional."""
    recipient = (to_email or os.getenv("RECEIPT_FALLBACK_EMAIL") or "").strip()
    subject = f"betty 购买收据 · {order_no}"
    body = (
        f"订单号: {order_no}\n"
        f"商品: {label}\n"
        f"积分: +{credits}\n"
        f"金额: ${amount_usd:.2f}\n"
        f"支付方式: {provider or 'n/a'}\n"
        f"商户: betty AI\n"
    )
    if extra:
        body += "\n".join(f"{k}: {v}" for k, v in extra.items()) + "\n"

    logger.info(
        "receipt_email stub: to=%s order=%s credits=%s amount_usd=%s",
        recipient or "(none)", order_no, credits, amount_usd,
    )

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_from = os.getenv("SMTP_FROM", "").strip()
    if not smtp_host or not smtp_from or not recipient:
        return {
            "sent": False,
            "reason": "smtp_or_recipient_missing",
            "order_no": order_no,
            "logged": True,
        }

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = recipient
        msg.set_content(body)
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        use_tls = os.getenv("SMTP_TLS", "true").lower() == "true"
        with smtplib.SMTP(smtp_host, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
        logger.info("receipt_email sent via SMTP to %s for %s", recipient, order_no)
        return {"sent": True, "order_no": order_no, "to": recipient}
    except Exception as e:
        logger.warning("receipt_email SMTP failed for %s: %s", order_no, e)
        return {"sent": False, "reason": str(e), "order_no": order_no, "logged": True}

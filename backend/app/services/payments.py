"""
Payment providers — WeChat Pay (Native 扫码), Alipay (precreate 当面付), and a
Sandbox fallback used for local end-to-end testing.

Design: each method returns the raw QR *content* (a weixin:// or alipay URL) that
the frontend renders as a QR code. Real provider calls are used when merchant
credentials are configured; otherwise a Sandbox order is created whose QR encodes
the local mock-confirm URL, so the full 下单→扫码→支付→发放 loop is testable now.
Going live only requires real merchant creds + a public HTTPS notify URL.
"""
from __future__ import annotations

import base64
import io
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)


def wechat_live() -> bool:
    return bool(settings.WECHAT_APPID and settings.WECHAT_MCHID
                and settings.WECHAT_API_V3_KEY
                and settings.WECHAT_PRIVATE_KEY_PATH
                and os.path.exists(settings.WECHAT_PRIVATE_KEY_PATH or ""))


def alipay_live() -> bool:
    return bool(settings.ALIPAY_APP_ID
                and settings.ALIPAY_APP_PRIVATE_KEY_PATH
                and os.path.exists(settings.ALIPAY_APP_PRIVATE_KEY_PATH or "")
                and settings.ALIPAY_PUBLIC_KEY_PATH
                and os.path.exists(settings.ALIPAY_PUBLIC_KEY_PATH or ""))


def method_status() -> dict:
    """Which payment methods are live vs sandbox, for the UI to display."""
    return {
        "wechat": {"live": wechat_live()},
        "alipay": {"live": alipay_live()},
        "stripe": {"live": bool(settings.STRIPE_API_KEY)},
    }


def qr_data_url(content: str) -> str:
    """Render QR content → a base64 PNG data URL (offline, no external service)."""
    import qrcode
    img = qrcode.make(content)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ── WeChat Pay Native ────────────────────────────────────
def create_wechat_native(order_no: str, amount_cny: float, description: str, notify_url: str) -> tuple[str, bool]:
    """Return (qr_content, is_live). Uses WeChat Pay v3 Native when configured."""
    if not wechat_live():
        return _sandbox_qr("wechat", order_no), False
    try:
        from wechatpayv3 import WeChatPay, WeChatPayType
        with open(settings.WECHAT_PRIVATE_KEY_PATH) as f:
            private_key = f.read()
        wxpay = WeChatPay(
            wechatpay_type=WeChatPayType.NATIVE,
            mchid=settings.WECHAT_MCHID,
            private_key=private_key,
            cert_serial_no=settings.WECHAT_CERT_SERIAL_NO,
            apiv3_key=settings.WECHAT_API_V3_KEY,
            appid=settings.WECHAT_APPID,
            notify_url=notify_url,
        )
        code, message = wxpay.pay(
            description=description,
            out_trade_no=order_no,
            amount={"total": int(round(amount_cny * 100))},  # fen
            pay_type=WeChatPayType.NATIVE,
        )
        import json as _j
        data = _j.loads(message) if message else {}
        code_url = data.get("code_url")
        if not code_url:
            raise RuntimeError(f"wechat native no code_url: {code} {message}")
        return code_url, True
    except Exception as e:
        logger.error("wechat native create failed: %s", e)
        raise


# ── Alipay precreate (当面付/扫码) ────────────────────────
def create_alipay_precreate(order_no: str, amount_cny: float, subject: str, notify_url: str) -> tuple[str, bool]:
    if not alipay_live():
        return _sandbox_qr("alipay", order_no), False
    try:
        from alipay import AliPay
        with open(settings.ALIPAY_APP_PRIVATE_KEY_PATH) as f:
            app_private_key = f.read()
        with open(settings.ALIPAY_PUBLIC_KEY_PATH) as f:
            alipay_public_key = f.read()
        client = AliPay(
            appid=settings.ALIPAY_APP_ID,
            app_notify_url=notify_url,
            app_private_key_string=app_private_key,
            alipay_public_key_string=alipay_public_key,
            sign_type="RSA2",
            debug=settings.ALIPAY_SANDBOX,
        )
        res = client.api_alipay_trade_precreate(
            out_trade_no=order_no,
            total_amount=str(round(amount_cny, 2)),
            subject=subject,
            notify_url=notify_url,
        )
        qr = res.get("qr_code")
        if not qr:
            raise RuntimeError(f"alipay precreate no qr_code: {res}")
        return qr, True
    except Exception as e:
        logger.error("alipay precreate failed: %s", e)
        raise


def _sandbox_qr(provider: str, order_no: str) -> str:
    """Sandbox QR encodes the local mock-confirm URL so scanning it on a phone
    (same network) would even complete the order. Clearly a test artifact."""
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/api/v1/billing/pay/mock-confirm/{order_no}?provider={provider}"


# ── Live status query (real providers) ───────────────────
def query_wechat(order_no: str) -> str:
    """Return 'paid' | 'pending' | 'failed' for a live WeChat order."""
    try:
        from wechatpayv3 import WeChatPay, WeChatPayType
        with open(settings.WECHAT_PRIVATE_KEY_PATH) as f:
            private_key = f.read()
        wxpay = WeChatPay(
            wechatpay_type=WeChatPayType.NATIVE, mchid=settings.WECHAT_MCHID,
            private_key=private_key, cert_serial_no=settings.WECHAT_CERT_SERIAL_NO,
            apiv3_key=settings.WECHAT_API_V3_KEY, appid=settings.WECHAT_APPID,
            notify_url=settings.PUBLIC_BASE_URL,
        )
        code, message = wxpay.query(out_trade_no=order_no)
        import json as _j
        state = (_j.loads(message).get("trade_state") if message else "") or ""
        return "paid" if state == "SUCCESS" else "pending"
    except Exception as e:
        logger.warning("wechat query failed: %s", e)
        return "pending"


def query_alipay(order_no: str) -> str:
    try:
        from alipay import AliPay
        with open(settings.ALIPAY_APP_PRIVATE_KEY_PATH) as f:
            app_private_key = f.read()
        with open(settings.ALIPAY_PUBLIC_KEY_PATH) as f:
            alipay_public_key = f.read()
        client = AliPay(appid=settings.ALIPAY_APP_ID, app_notify_url=settings.PUBLIC_BASE_URL,
                        app_private_key_string=app_private_key, alipay_public_key_string=alipay_public_key,
                        sign_type="RSA2", debug=settings.ALIPAY_SANDBOX)
        res = client.api_alipay_trade_query(out_trade_no=order_no)
        status = res.get("trade_status", "")
        return "paid" if status in ("TRADE_SUCCESS", "TRADE_FINISHED") else "pending"
    except Exception as e:
        logger.warning("alipay query failed: %s", e)
        return "pending"

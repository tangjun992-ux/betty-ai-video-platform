"""
PaymentOrder — a persisted payment order for credit purchases via WeChat Pay /
Alipay / Stripe (or sandbox). Persisted so status polling + async notify are
reliable and credit granting is idempotent (grant only once when paid).
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text

from app.models.base import Base


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    order_no = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True, default=0)

    provider = Column(String(20), nullable=False)   # wechat | alipay | stripe | sandbox
    kind = Column(String(20), nullable=False)        # plan | pack
    item_id = Column(String(60), nullable=False)
    cycle = Column(String(20), nullable=True)

    credits = Column(Integer, nullable=False)
    amount_usd = Column(Float, nullable=False)
    amount_cny = Column(Float, nullable=False)
    label = Column(String(200), nullable=True)

    status = Column(String(20), nullable=False, default="pending")  # pending | paid | expired | failed
    qr_content = Column(Text, nullable=True)         # raw code_url / qr_code to render as QR
    provider_txn_id = Column(String(128), nullable=True)
    granted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<PaymentOrder {self.order_no} {self.provider} {self.status}>"

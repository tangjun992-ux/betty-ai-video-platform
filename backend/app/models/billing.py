from enum import Enum
from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime, timezone


class TransactionType(str, Enum):
    PURCHASE = "purchase"       # User bought credits
    CONSUMPTION = "consumption"  # Task consumed credits
    REFUND = "refund"            # Refund for failed task
    BONUS = "bonus"              # System bonus
    DAILY_FREE = "daily_free"    # Free daily credits


class Transaction(Base):
    __tablename__ = "transactions"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(String(36), nullable=True, index=True)
    team_id = Column(String(36), nullable=True, index=True)

    type = Column(String(20), nullable=False)
    amount = Column(Integer, nullable=False)
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)

    description = Column(String(500), nullable=True)
    amount_usd = Column(Float, nullable=True)
    model_used = Column(String(100), nullable=True)

    payment_method = Column(String(50), nullable=True)
    payment_id = Column(String(100), nullable=True)

    user = relationship("User")

    def __repr__(self):
        return f"<Transaction #{self.id} {self.type} {self.amount:+d}>"


class UserBalance(Base):
    """Current credit balance per user"""
    __tablename__ = "user_balance"

    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    credits = Column(Integer, nullable=False, default=0)

    daily_credits = Column(Integer, default=0)
    daily_credits_max = Column(Integer, default=10)
    last_reset_date = Column(DateTime(timezone=True), nullable=True)
    # Subscription allotment with rollover cap (≤ 2× monthly plan credits).
    plan_credits = Column(Integer, nullable=False, default=0)
    plan_monthly_allotment = Column(Integer, nullable=False, default=0)

    total_spent = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    total_purchased = Column(Integer, default=0)

    user = relationship("User", back_populates="balance")

    def __repr__(self):
        return f"<Balance #{self.user_id} credits={self.credits}>"

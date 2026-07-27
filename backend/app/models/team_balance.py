"""Shared credit pool per team (对标 Yapper / Runway 团队席位计费)."""
from sqlalchemy import Column, String, Integer, DateTime

from app.models.base import Base


class TeamBalance(Base):
    __tablename__ = "team_balance"

    team_id = Column(String(36), unique=True, nullable=False, index=True)
    credits = Column(Integer, nullable=False, default=0)
    daily_credits = Column(Integer, default=0)
    daily_credits_max = Column(Integer, default=0)
    last_reset_date = Column(DateTime(timezone=True), nullable=True)
    total_spent = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    total_purchased = Column(Integer, default=0)

    def __repr__(self):
        return f"<TeamBalance {self.team_id} credits={self.credits}>"

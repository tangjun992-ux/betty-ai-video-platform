"""Director 会话持久化 model — 对标 yapper Sessions。"""
from sqlalchemy import Column, String, Text, Integer, JSON
from app.models.base import Base


class DirectorSession(Base):
    __tablename__ = "director_sessions"

    session_uid = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    user_id = Column(Integer, index=True, nullable=True, default=0)            # 0 = guest/LOCAL_MODE
    title = Column(String(200), nullable=False, default="新导演会话")
    brief = Column(Text, nullable=True)
    intent = Column(String(40), nullable=True)
    plan = Column(JSON, nullable=True)      # DirectorPlan.to_dict()
    assets = Column(JSON, nullable=True)    # 执行产出的资产列表
    status = Column(String(20), nullable=False, default="draft")  # draft | planned | done

    def __repr__(self):
        return f"<DirectorSession {self.session_uid} {self.status}>"

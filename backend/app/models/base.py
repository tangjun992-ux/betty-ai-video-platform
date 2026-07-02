from datetime import datetime
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {c.key: getattr(self, c.key) for c in self.__table__.columns}

from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    role = Column(String(20), default="free")  # free | creator | pro | enterprise
    
    # Profile
    display_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Preferences
    default_model = Column(String(50), nullable=True, default="auto")
    default_quality = Column(String(20), nullable=True, default="balanced")
    
    metadata_json = Column(Text, nullable=True)  # additional preferences as JSON

    # Relationships
    tasks = relationship("Task", back_populates="user", lazy="selectin")
    balance = relationship("UserBalance", back_populates="user", uselist=False, lazy="selectin")

    def __repr__(self):
        return f"<User #{self.id} {self.username}>"

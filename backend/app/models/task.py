from enum import Enum
from sqlalchemy import Column, String, Text, Integer, Float, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime, timezone

class TaskStatus(str, Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    ROUTING = "routing"
    GENERATING = "generating"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    MIXED = "mixed"

class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Input
    prompt = Column(Text, nullable=False)
    media_type = Column(String(20), nullable=False, default="auto")  # image | video | auto
    quality = Column(String(20), nullable=False, default="balanced")  # fast | balanced | high
    
    # Model selection
    requested_model = Column(String(50), nullable=True, default="auto")
    selected_model = Column(String(100), nullable=True)
    fallback_model = Column(String(100), nullable=True)
    
    # Parameters
    parameters = Column(JSON, nullable=True)  # resolution, duration, count, style, etc.
    
    # Status tracking
    status = Column(String(20), nullable=False, default="queued", index=True)
    progress = Column(Integer, default=0)  # 0-100
    current_stage = Column(String(30), nullable=True)  # analyzing | routing | generating | uploading
    
    # Celery task info
    celery_task_id = Column(String(50), nullable=True, index=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    
    # Cost
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    
    # Results (JSON)
    results = Column(JSON, nullable=True)
    # Structure: [{"type": "image", "url": "...", "thumbnail": "...", "model": "..." }]
    
    # Error
    error_message = Column(Text, nullable=True)
    
    # Webhook
    webhook_url = Column(String(500), nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.task_id} {self.status}>"


class TaskResult(Base):
    """Individual result item for multi-output tasks"""
    __tablename__ = "task_results"

    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    media_type = Column(String(20), nullable=False)  # image | video
    media_url = Column(String(1000), nullable=False)
    thumbnail_url = Column(String(1000), nullable=True)
    duration = Column(Float, nullable=True)  # seconds for video
    resolution = Column(String(20), nullable=True)  # e.g., "1920x1080"
    model_used = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=True)  # bytes
    metadata_json = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<TaskResult {self.media_type} {self.id}>"

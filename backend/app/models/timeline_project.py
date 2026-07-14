"""
Timeline project model — persist multi-clip editor projects per user.
"""
from sqlalchemy import Column, String, Integer, JSON

from app.models.base import Base


class TimelineProject(Base):
    __tablename__ = "timeline_projects"

    project_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    user_id = Column(Integer, nullable=True, index=True, default=0)
    name = Column(String(200), nullable=False, default="未命名项目")
    # list[{url, start, end, transition, label}]
    clips = Column(JSON, nullable=False, default=list)
    # narration, subtitles, transition defaults
    settings = Column(JSON, nullable=True, default=dict)

    def to_api_dict(self) -> dict:
        return {
            "id": self.project_id,
            "name": self.name,
            "clips": self.clips if isinstance(self.clips, list) else [],
            "settings": self.settings if isinstance(self.settings, dict) else {},
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }

    def __repr__(self):
        return f"<TimelineProject {self.project_id} {self.name}>"

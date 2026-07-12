"""
Project model — organize creations into named projects/collections
(对标 Runway / Yapper 的 Projects). Items are stored as a JSON list of
library references so a project can span uploads + generated assets.
"""
from sqlalchemy import Column, String, Integer, Text, JSON

from app.models.base import Base


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    user_id = Column(Integer, nullable=True, index=True, default=0)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    cover = Column(String(1000), nullable=True)
    # list[{item_id, url, thumbnail, media_type, title}]
    items = Column(JSON, nullable=False, default=list)

    def __repr__(self):
        return f"<Project {self.project_id} {self.name}>"

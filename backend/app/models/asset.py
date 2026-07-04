"""
Asset model — user-uploaded files tracked in the content library.
Generated content lives in Task.results; the library API merges both.
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey

from app.models.base import Base


class Asset(Base):
    __tablename__ = "assets"

    asset_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    media_type = Column(String(20), nullable=False)  # image | video | audio
    url = Column(String(1000), nullable=False)
    thumbnail = Column(String(1000), nullable=True)

    filename = Column(String(255), nullable=True)  # original filename
    size_bytes = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)
    note = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Asset {self.asset_id} {self.media_type}>"

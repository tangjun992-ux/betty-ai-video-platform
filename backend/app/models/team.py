"""Team collaboration models — minimal Team + TeamMember."""
from sqlalchemy import Column, String, Integer, Text

from app.models.base import Base


class Team(Base):
    __tablename__ = "teams"

    team_id = Column(String(36), unique=True, nullable=False, index=True)
    owner_user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    # project visibility: private | team | public
    default_visibility = Column(String(20), nullable=False, default="team")
    seat_limit = Column(Integer, nullable=False, default=5)

    def __repr__(self):
        return f"<Team {self.team_id} {self.name}>"


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id = Column(String(36), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False, default="member")  # owner | admin | member
    invite_email = Column(String(255), nullable=True)
    invite_username = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="active")  # pending | active

    def __repr__(self):
        return f"<TeamMember team={self.team_id} user={self.user_id}>"

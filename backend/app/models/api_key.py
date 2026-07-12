"""
ApiKey — platform API keys for the public developer API.

The full secret (sk_betty_...) is shown ONCE at creation and only its SHA-256
hash is stored. Requests authenticate with X-API-Key / Bearer; the hash is
looked up to resolve the owning user for per-account scoping + billing.
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime

from app.models.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys_platform"

    key_id = Column(String(40), unique=True, nullable=False, index=True)   # public prefix, e.g. betty_live_ab12cd
    key_hash = Column(String(64), nullable=False, index=True)              # sha256 of the full secret
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(120), nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<ApiKey {self.key_id} user={self.user_id} revoked={self.revoked}>"

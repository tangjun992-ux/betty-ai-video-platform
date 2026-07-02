"""
JWT Authentication — token-based auth system.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.config import settings
from app.models.user import User
from sqlalchemy import select

# Security
# Security — using hashlib to avoid passlib/bcrypt compatibility issues
import hashlib
import secrets

def _hash_password(password: str, salt: str = "") -> str:
    if not salt:
        salt = secrets.token_hex(16)
    return f"{salt}${hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    salt, hash_hex = hashed_password.split("$", 1)
    return hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), 100000).hex() == hash_hex

def get_password_hash(password: str) -> str:
    return _hash_password(password)


security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.JWT_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate current user from JWT token."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.execute(select(User).where(User.id == user_id))
    user = user.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get user if authenticated, else None."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin user."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user

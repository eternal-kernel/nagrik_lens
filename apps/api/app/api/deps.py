import os
from typing import Generator
from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "dev-secret-key")


def verify_admin_key(
    x_admin_key: str | None = Header(None, alias="X-Admin-Key")
) -> str:
    """Validate X-Admin-Key header for admin endpoints."""
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Admin-Key header is missing",
        )
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )
    return x_admin_key

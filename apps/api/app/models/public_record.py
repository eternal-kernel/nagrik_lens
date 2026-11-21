from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.election import Candidate


class PublicActivityRecord(Base):
    __tablename__ = "public_activity_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    record_type: Mapped[str] = mapped_column(String(50), nullable=False)
    period_label: Mapped[str] = mapped_column(String(100), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    structured_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="needs_review"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="public_activity_records")

    def __repr__(self) -> str:
        return (
            f"<PublicActivityRecord(id={self.id}, candidate_id={self.candidate_id}, "
            f"type='{self.record_type}', period='{self.period_label}', status='{self.verification_status}')>"
        )

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Affidavit(Base):
    __tablename__ = "affidavits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    publication_status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    redaction_boxes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="affidavits")
    disclosures: Mapped[List["Disclosure"]] = relationship(
        "Disclosure", back_populates="affidavit", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Affidavit(id={self.id}, candidate_id={self.candidate_id}, filing_date={self.filing_date}, pub_status='{self.publication_status}')>"


class Disclosure(Base):
    __tablename__ = "disclosures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    affidavit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("affidavits.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # education | movable_assets | immovable_assets | liabilities | pending_criminal_cases | convictions
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # self | spouse | huf | dependent_1 | dependent_2 | dependent_3 | joint
    structured_value: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    raw_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft"
    )  # draft | needs_review | verified | rejected
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    affidavit: Mapped["Affidavit"] = relationship("Affidavit", back_populates="disclosures")
    review_events: Mapped[List["ReviewEvent"]] = relationship(
        "ReviewEvent", back_populates="disclosure", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Disclosure(id={self.id}, category='{self.category}', field_key='{self.field_key}', status='{self.verification_status}')>"


class ReviewEvent(Base):
    __tablename__ = "review_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    disclosure_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("disclosures.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    disclosure: Mapped["Disclosure"] = relationship("Disclosure", back_populates="review_events")

    def __repr__(self) -> str:
        return f"<ReviewEvent(id={self.id}, disclosure_id={self.disclosure_id}, action='{self.action}', reviewer='{self.reviewer_name}')>"

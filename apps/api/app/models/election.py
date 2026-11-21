from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.affidavit import Affidavit
    from app.models.public_record import PublicActivityRecord


class Election(Base):
    __tablename__ = "elections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    election_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Lok Sabha", "Assembly"
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    constituencies: Mapped[List["Constituency"]] = relationship(
        "Constituency", back_populates="election", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Election(id={self.id}, name='{self.name}', year={self.year}, state='{self.state}')>"


class Constituency(Base):
    __tablename__ = "constituencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    election_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("elections.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    election: Mapped["Election"] = relationship("Election", back_populates="constituencies")
    candidates: Mapped[List["Candidate"]] = relationship(
        "Candidate", back_populates="constituency", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Constituency(id={self.id}, code='{self.code}', name='{self.name}')>"


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    constituency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("constituencies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    party_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_fictional: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prior_office_held: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    constituency: Mapped["Constituency"] = relationship("Constituency", back_populates="candidates")
    affidavits: Mapped[List["Affidavit"]] = relationship(
        "Affidavit", back_populates="candidate", cascade="all, delete-orphan"
    )
    public_activity_records: Mapped[List["PublicActivityRecord"]] = relationship(
        "PublicActivityRecord", back_populates="candidate", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Candidate(id={self.id}, name='{self.name}', party='{self.party_name}', fictional={self.is_fictional})>"

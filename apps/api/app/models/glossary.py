from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LegalGlossary(Base):
    __tablename__ = "legal_glossary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    act_name: Mapped[str] = mapped_column(String(255), nullable=False)
    term_en: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation_en: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_te: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_hi: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="verified")

    def __repr__(self) -> str:
        return f"<LegalGlossary(code_key='{self.code_key}', act='{self.act_name}', term='{self.term_en}')>"

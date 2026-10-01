import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnnualBaseline(Base):
    __tablename__ = "annual_baselines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), unique=True, nullable=False)
    fiscal_year: Mapped[str] = mapped_column(String(10), nullable=False)
    timeline_content: Mapped[str] = mapped_column(Text, nullable=False)
    key_themes: Mapped[str | None] = mapped_column(Text)
    signal_count: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

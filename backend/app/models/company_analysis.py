import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CompanyAnalysis(Base):
    __tablename__ = "company_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), unique=True, nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, default=0)
    filing_count: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

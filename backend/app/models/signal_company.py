import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SignalCompanyMatch(Base):
    __tablename__ = "signal_company_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id: Mapped[str] = mapped_column(String(36), ForeignKey("signals.id"), nullable=False)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    match_score: Mapped[float | None] = mapped_column(Float)
    match_type: Mapped[str | None] = mapped_column(String(20))
    match_reason: Mapped[str | None] = mapped_column(Text)
    talking_points: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

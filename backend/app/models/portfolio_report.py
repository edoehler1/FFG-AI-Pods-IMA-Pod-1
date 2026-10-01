import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortfolioReport(Base):
    __tablename__ = "portfolio_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_data: Mapped[str] = mapped_column(Text, nullable=False)
    company_count: Mapped[int] = mapped_column(Integer, default=0)
    industries: Mapped[str | None] = mapped_column(Text)
    days_back: Mapped[int] = mapped_column(Integer, default=7)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

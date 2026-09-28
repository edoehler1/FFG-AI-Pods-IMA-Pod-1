import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    industry: Mapped[str | None] = mapped_column(String(50))
    sub_sector: Mapped[str | None] = mapped_column(String(100))
    signal_type: Mapped[str | None] = mapped_column(String(50))
    news_category: Mapped[str | None] = mapped_column(String(20))
    dedupe_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

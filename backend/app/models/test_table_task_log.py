"""Database model for detailed test table task logs."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.config.database import Base


class TestTableTaskLog(Base):
    """Structured log entries for test table generation tasks."""

    __tablename__ = "test_table_task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(36), ForeignKey("test_table_tasks.id"), nullable=False, index=True)

    log_level = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    phase = Column(String(50), nullable=True, index=True)
    progress_percentage = Column(Float, nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


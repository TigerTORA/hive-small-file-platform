from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class ScanTaskLogDB(Base):
    __tablename__ = "scan_task_logs"

    id = Column(Integer, primary_key=True, index=True)
    scan_task_id = Column(Integer, ForeignKey("scan_tasks.id"), nullable=False, index=True)

    # Log content
    level = Column(String(20), nullable=False, index=True)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    database_name = Column(String(255), nullable=True)
    table_name = Column(String(255), nullable=True)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationship (optional backref not required for now)
    # scan_task = relationship("ScanTask", back_populates="logs")


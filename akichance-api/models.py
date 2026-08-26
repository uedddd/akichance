from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base

class Seat(Base):
    __tablename__ = "seats"  # テーブル名

    seat_id    = Column(Integer, primary_key=True, index=True)
    floor_id   = Column(Integer, nullable=False)
    seat_name  = Column(String(20), nullable=False)
    status     = Column(String(10), nullable=False, default="empty")
    is_active  = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
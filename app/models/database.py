"""Database models."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Team(Base):
    """Team model for managing API tokens and quotas."""
    
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    quota_tokens = Column(Integer, nullable=False)  # Total allowed tokens
    used_tokens = Column(Integer, default=0, nullable=False)  # Tokens used so far
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    logs = relationship("RequestLog", back_populates="team", cascade="all, delete-orphan")


class RequestLog(Base):
    """Request log for tracking individual API calls."""
    
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    model = Column(String(100), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    status = Column(String(50), nullable=False)  # success, error, quota_exceeded
    error_message = Column(Text, nullable=True)
    
    # Relationship
    team = relationship("Team", back_populates="logs")


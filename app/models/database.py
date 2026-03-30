"""Database models."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Team(Base):
    """Team model for managing API tokens and budgets."""
    
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    
    # USD-based budget system
    budget_usd = Column(Float, nullable=False, default=5.0)  # Total budget in USD
    used_usd = Column(Float, default=0.0, nullable=False)  # USD spent so far
    
    # Token tracking (for statistics)
    total_tokens_used = Column(Integer, default=0, nullable=False)  # Cumulative tokens used
    
    max_requests_per_minute = Column(Integer, default=60, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    logs = relationship("RequestLog", back_populates="team", cascade="all, delete-orphan")
    
    @property
    def remaining_usd(self) -> float:
        """Calculate remaining budget in USD."""
        return max(0.0, self.budget_usd - self.used_usd)


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
    cost_usd = Column(Float, default=0.0)  # Cost of this request in USD
    status = Column(String(50), nullable=False)  # success, error, quota_exceeded
    error_message = Column(Text, nullable=True)
    request_payload = Column(Text, nullable=True)
    response_payload = Column(Text, nullable=True)
    
    # Relationship
    team = relationship("Team", back_populates="logs")

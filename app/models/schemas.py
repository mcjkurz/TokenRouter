"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List, Any, Dict, Union
from pydantic import BaseModel, Field, field_validator
import re


# Team schemas
class TeamBase(BaseModel):
    """Base team schema."""
    name: str
    budget_usd: float = Field(gt=0, description="Budget in USD for the team")
    max_requests_per_minute: int = Field(default=30, gt=0, description="Rate limit per minute")


class TeamCreate(TeamBase):
    """Schema for creating a team."""
    email: Optional[str] = None
    token: Optional[str] = None  # Auto-generate if not provided


class TeamUpdate(BaseModel):
    """Schema for updating a team."""
    name: Optional[str] = None
    budget_usd: Optional[float] = Field(None, gt=0)
    max_requests_per_minute: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None


class TeamResponse(TeamBase):
    """Schema for team response."""
    id: int
    email: Optional[str] = None
    token: str
    used_usd: float
    total_tokens_used: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TeamStats(TeamResponse):
    """Extended team schema with statistics."""
    remaining_usd: float
    usage_percentage: float
    total_requests: int


# Request log schemas
class RequestLogResponse(BaseModel):
    """Schema for request log response."""
    id: int
    team_id: int
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    status: str
    error_message: Optional[str]
    request_payload: Optional[str]
    response_payload: Optional[str]
    
    class Config:
        from_attributes = True


# Chat completion schemas (OpenAI-compatible)
class ChatMessage(BaseModel):
    """Chat message schema."""
    model_config = {"extra": "allow"}
    
    role: str
    content: Union[str, List[Dict[str, Any]], None] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """Chat completion request schema. Allows extra fields to pass through for full OpenAI compatibility."""
    model_config = {"extra": "allow"}
    
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None


class UsageInfo(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Chat completion response schema."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: UsageInfo


# Admin stats
class AdminStats(BaseModel):
    """Overall admin statistics."""
    total_teams: int
    active_teams: int
    total_requests: int
    total_tokens_used: int
    total_budget_usd: float
    total_used_usd: float


# Registration schemas
class RegistrationRequest(BaseModel):
    """Schema for user registration request."""
    username: str = Field(..., min_length=5, max_length=50, description="Username for the account (letters, numbers, underscores)")
    email: str = Field(..., description="Email address (must be from allowed domain)")
    access_code: str = Field(..., description="Registration access code")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate that username contains only letters, numbers, and underscores."""
        v = v.strip()
        if ' ' in v:
            raise ValueError('Username cannot contain spaces')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only letters, numbers, and underscores')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Basic email validation and sanitization."""
        v = v.strip().lower()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v
    
    @field_validator('access_code')
    @classmethod
    def validate_access_code(cls, v: str) -> str:
        """Sanitize access code."""
        return v.strip()


class RegistrationResponse(BaseModel):
    """Schema for successful registration response."""
    message: str
    username: str
    email: str
    api_key: str
    api_base_url: Optional[str] = None
    budget_usd: float
    warning: str
    usage_example: Optional[str] = None

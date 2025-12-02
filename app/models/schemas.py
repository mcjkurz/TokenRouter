"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, field_validator
import re


# Team schemas
class TeamBase(BaseModel):
    """Base team schema."""
    name: str
    quota_tokens: int = Field(gt=0, description="Token quota for the team")
    max_requests_per_minute: int = Field(default=30, gt=0, description="Rate limit per minute")


class TeamCreate(TeamBase):
    """Schema for creating a team."""
    email: Optional[str] = None  # Optional email address
    token: Optional[str] = None  # Auto-generate if not provided


class TeamUpdate(BaseModel):
    """Schema for updating a team."""
    name: Optional[str] = None
    quota_tokens: Optional[int] = Field(None, gt=0)
    max_requests_per_minute: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None


class TeamResponse(TeamBase):
    """Schema for team response."""
    id: int
    email: Optional[str] = None
    token: str
    used_tokens: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TeamStats(TeamResponse):
    """Extended team schema with statistics."""
    remaining_tokens: int
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
    status: str
    error_message: Optional[str]
    request_payload: Optional[str]  # JSON string
    response_payload: Optional[str]  # JSON string
    
    class Config:
        from_attributes = True


# Chat completion schemas (OpenAI-compatible)
class ChatMessage(BaseModel):
    """Chat message schema."""
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat completion request schema."""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    # Add other OpenAI parameters as needed


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
    total_quota_tokens: int


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
        # Strip whitespace
        v = v.strip()
        
        # Check for spaces
        if ' ' in v:
            raise ValueError('Username cannot contain spaces')
        
        # Check alphanumeric (allows underscores)
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only letters, numbers, and underscores')
        
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Basic email validation and sanitization."""
        v = v.strip().lower()
        
        # Basic format check (more thorough validation happens in the API)
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        
        return v
    
    @field_validator('access_code')
    @classmethod
    def validate_access_code(cls, v: str) -> str:
        """Sanitize access code."""
        # Strip whitespace but don't modify the code itself
        return v.strip()


class RegistrationResponse(BaseModel):
    """Schema for successful registration response."""
    message: str
    username: str
    email: str
    api_key: str
    api_base_url: Optional[str] = None
    quota_tokens: int
    warning: str
    usage_example: Optional[str] = None


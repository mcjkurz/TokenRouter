"""Authentication and token validation."""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.models.database import Team
from app.core.database import get_db

# In-memory rate limiting tracker
_rate_limit_tracker: Dict[int, List[datetime]] = {}


def validate_team_token(
    authorization: str = Header(..., description="Bearer token for team authentication"),
    db: Session = Depends(get_db)
) -> Team:
    """
    Validate team token and return team object.
    
    Args:
        authorization: Authorization header (Bearer token)
        db: Database session
    
    Returns:
        Team object if valid
    
    Raises:
        HTTPException: If token is invalid or team is inactive
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use 'Bearer <token>'"
        )
    
    token = authorization.replace("Bearer ", "").strip()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not provided"
        )
    
    team = db.query(Team).filter(Team.token == token).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    if not team.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team is inactive"
        )
    
    return team


def check_quota(team: Team) -> None:
    """
    Check if team has remaining quota.
    
    Args:
        team: Team object
    
    Raises:
        HTTPException: If quota is exceeded
    """
    remaining = team.quota_tokens - team.used_tokens
    if team.used_tokens >= team.quota_tokens:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Token quota exceeded. "
                f"Used: {team.used_tokens}/{team.quota_tokens} tokens. "
                f"Remaining: 0 tokens. "
                f"Check your usage at GET /v1/usage"
            )
        )


def check_rate_limit(team: Team) -> None:
    """
    Check if team is within rate limit.
    
    Args:
        team: Team object
    
    Raises:
        HTTPException: If rate limit is exceeded
    """
    now = datetime.utcnow()
    one_minute_ago = now - timedelta(minutes=1)
    
    # Get or initialize request history for this team
    if team.id not in _rate_limit_tracker:
        _rate_limit_tracker[team.id] = []
    
    # Remove requests older than 1 minute
    _rate_limit_tracker[team.id] = [
        ts for ts in _rate_limit_tracker[team.id] if ts > one_minute_ago
    ]
    
    # Check if limit exceeded
    current_count = len(_rate_limit_tracker[team.id])
    if current_count >= team.max_requests_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {team.max_requests_per_minute} requests per minute. Try again in a few seconds."
        )
    
    # Add current request
    _rate_limit_tracker[team.id].append(now)


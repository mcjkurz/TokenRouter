"""Authentication and token validation."""
import logging
import threading
from typing import Dict, List
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.models.database import Team
from app.core.database import get_db

logger = logging.getLogger("uvicorn.error")


def _obfuscate(s: str) -> str:
    """Show only the first/last few characters of a secret string."""
    if len(s) < 12:
        return s[:2] + "***" + s[-2:] if len(s) > 4 else "***"
    return s[:4] + "***" + s[-4:]


# In-memory rate limiting tracker (thread-safe)
_rate_limit_lock = threading.Lock()
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
        logger.warning(f"[auth] Invalid token: {_obfuscate(token)}")
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


def check_budget(team: Team) -> None:
    """
    Check if team has remaining budget (pre-check only, not atomic).
    
    NOTE: This is a soft pre-check for fast rejection of clearly over-budget
    requests. The actual budget enforcement happens via reserve_budget() in
    the usage service, which uses atomic DB operations.
    
    Args:
        team: Team object
    
    Raises:
        HTTPException: If budget is clearly exceeded
    """
    if team.used_usd >= team.budget_usd:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Budget exceeded. "
                f"Used: ${team.used_usd:.2f}/${team.budget_usd:.2f}. "
                f"Remaining: $0.00. "
                f"Check your usage at GET /v1/usage/{team.token}"
            )
        )


def check_rate_limit(team: Team) -> None:
    """
    Check if team is within rate limit (thread-safe).
    
    Args:
        team: Team object
    
    Raises:
        HTTPException: If rate limit is exceeded
    """
    now = datetime.now(timezone.utc)
    one_minute_ago = now - timedelta(minutes=1)
    
    with _rate_limit_lock:
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


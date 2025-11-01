"""Authentication and token validation."""
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.models.database import Team
from app.core.database import get_db


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
    if team.used_tokens >= team.quota_tokens:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Token quota exceeded. Used: {team.used_tokens}/{team.quota_tokens}"
        )


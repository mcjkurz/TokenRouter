"""Admin API endpoints for team management."""
import os
import secrets
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.config import settings
from app.models.database import Team, RequestLog
from app.models.schemas import (
    TeamCreate, TeamUpdate, TeamResponse, TeamStats,
    RequestLogResponse, AdminStats
)

# Get the project root directory (parent of 'app' folder)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_password(x_admin_password: str = Header(None)):
    """Verify admin password from header."""
    if not x_admin_password or x_admin_password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password"
        )
    return True


def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


@router.get("/stats", response_model=AdminStats)
def get_admin_stats(
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_admin_password)
):
    """Get overall system statistics."""
    total_teams = db.query(Team).count()
    active_teams = db.query(Team).filter(Team.is_active == True).count()
    total_requests = db.query(RequestLog).count()
    total_tokens_used = db.query(func.sum(Team.used_tokens)).scalar() or 0
    total_quota_tokens = db.query(func.sum(Team.quota_tokens)).scalar() or 0
    
    return AdminStats(
        total_teams=total_teams,
        active_teams=active_teams,
        total_requests=total_requests,
        total_tokens_used=total_tokens_used,
        total_quota_tokens=total_quota_tokens
    )


@router.get("/teams", response_model=List[TeamStats])
def list_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_admin_password)
):
    """List all teams with statistics."""
    teams = db.query(Team).offset(skip).limit(limit).all()
    
    result = []
    for team in teams:
        total_requests = db.query(RequestLog).filter(RequestLog.team_id == team.id).count()
        remaining_tokens = max(0, team.quota_tokens - team.used_tokens)
        usage_percentage = (team.used_tokens / team.quota_tokens * 100) if team.quota_tokens > 0 else 0
        
        result.append(TeamStats(
            id=team.id,
            name=team.name,
            email=team.email,
            token=team.token,
            quota_tokens=team.quota_tokens,
            used_tokens=team.used_tokens,
            is_active=team.is_active,
            created_at=team.created_at,
            remaining_tokens=remaining_tokens,
            usage_percentage=round(usage_percentage, 2),
            total_requests=total_requests
        ))
    
    return result


@router.get("/teams/{team_id}", response_model=TeamStats)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_admin_password)
):
    """Get team details by ID."""
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found"
        )
    
    total_requests = db.query(RequestLog).filter(RequestLog.team_id == team.id).count()
    remaining_tokens = max(0, team.quota_tokens - team.used_tokens)
    usage_percentage = (team.used_tokens / team.quota_tokens * 100) if team.quota_tokens > 0 else 0
    
    return TeamStats(
        id=team.id,
        name=team.name,
        email=team.email,
        token=team.token,
        quota_tokens=team.quota_tokens,
        used_tokens=team.used_tokens,
        is_active=team.is_active,
        created_at=team.created_at,
        remaining_tokens=remaining_tokens,
        usage_percentage=round(usage_percentage, 2),
        total_requests=total_requests
    )


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    team_data: TeamCreate,
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_admin_password)
):
    """Create a new team."""
    # Check if team name already exists
    existing_team = db.query(Team).filter(Team.name == team_data.name).first()
    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team with name '{team_data.name}' already exists"
        )
    
    # Check if email already exists (if email provided)
    if team_data.email:
        existing_email = db.query(Team).filter(Team.email == team_data.email.lower()).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team with email '{team_data.email}' already exists"
            )
    
    # Generate token if not provided
    token = team_data.token if team_data.token else generate_token()
    
    # Check if token already exists
    existing_token = db.query(Team).filter(Team.token == token).first()
    if existing_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token already exists"
        )
    
    # Create team
    team = Team(
        name=team_data.name,
        email=team_data.email.lower() if team_data.email else None,
        token=token,
        quota_tokens=team_data.quota_tokens,
        max_requests_per_minute=team_data.max_requests_per_minute,
        used_tokens=0,
        is_active=True
    )
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    return team


@router.put("/teams/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: int,
    team_data: TeamUpdate,
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_admin_password)
):
    """Update team details."""
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found"
        )
    
    # Update fields
    if team_data.name is not None:
        # Check if new name conflicts with existing team
        existing = db.query(Team).filter(
            Team.name == team_data.name,
            Team.id != team_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team with name '{team_data.name}' already exists"
            )
        team.name = team_data.name
    
    if team_data.quota_tokens is not None:
        team.quota_tokens = team_data.quota_tokens
    
    if team_data.max_requests_per_minute is not None:
        team.max_requests_per_minute = team_data.max_requests_per_minute
    
    if team_data.is_active is not None:
        team.is_active = team_data.is_active
    
    db.commit()
    db.refresh(team)
    
    return team


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_admin_password)
):
    """Delete a team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found"
        )
    
    db.delete(team)
    db.commit()


@router.post("/teams/{team_id}/reset", response_model=TeamResponse)
def reset_team_usage(
    team_id: int,
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_admin_password)
):
    """Reset team's token usage counter."""
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found"
        )
    
    team.used_tokens = 0
    db.commit()
    db.refresh(team)
    
    return team


@router.get("/teams/{team_id}/logs", response_model=List[RequestLogResponse])
def get_team_logs(
    team_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_admin_password)
):
    """Get request logs for a specific team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found"
        )
    
    logs = db.query(RequestLog).filter(
        RequestLog.team_id == team_id
    ).order_by(
        RequestLog.timestamp.desc()
    ).offset(skip).limit(limit).all()
    
    return logs


@router.get("/server-logs")
def list_server_logs(
    authenticated: bool = Depends(verify_admin_password)
):
    """List all available server log files."""
    if not os.path.exists(LOGS_DIR):
        return []
    
    log_files = []
    for filename in os.listdir(LOGS_DIR):
        if filename.endswith('.log'):
            filepath = os.path.join(LOGS_DIR, filename)
            stat = os.stat(filepath)
            log_files.append({
                "filename": filename,
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
    
    # Sort by modified time, newest first
    log_files.sort(key=lambda x: x["modified"], reverse=True)
    return log_files


@router.get("/server-logs/{filename}", response_class=PlainTextResponse)
def get_server_log_content(
    filename: str,
    authenticated: bool = Depends(verify_admin_password)
):
    """Get the content of a specific server log file."""
    # Security: prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
    
    if not filename.endswith('.log'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type"
        )
    
    filepath = os.path.join(LOGS_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log file '{filename}' not found"
        )
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading log file: {str(e)}"
        )


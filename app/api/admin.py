"""Admin API endpoints for team management."""
import hmac
import os
import secrets
import threading
import time
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Request
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

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

router = APIRouter(prefix="/admin", tags=["admin"])

_login_attempts_lock = threading.Lock()
_login_attempts: Dict[str, List[float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300


def _check_login_rate_limit(client_ip: str) -> None:
    """Check if client has exceeded login attempt limit."""
    now = time.time()
    window_start = now - LOGIN_WINDOW_SECONDS
    
    with _login_attempts_lock:
        if client_ip not in _login_attempts:
            _login_attempts[client_ip] = []
        
        _login_attempts[client_ip] = [
            t for t in _login_attempts[client_ip] if t > window_start
        ]
        
        if len(_login_attempts[client_ip]) >= MAX_LOGIN_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Try again in {LOGIN_WINDOW_SECONDS // 60} minutes."
            )


def _record_login_attempt(client_ip: str) -> None:
    """Record a failed login attempt."""
    with _login_attempts_lock:
        if client_ip not in _login_attempts:
            _login_attempts[client_ip] = []
        _login_attempts[client_ip].append(time.time())


def verify_admin_password(
    request: Request,
    x_admin_password: str = Header(None)
):
    """Verify admin password from header with brute-force protection."""
    client_ip = request.client.host if request.client else "unknown"
    
    _check_login_rate_limit(client_ip)
    
    if not x_admin_password or not hmac.compare_digest(
        x_admin_password.encode('utf-8'),
        settings.admin_password.encode('utf-8')
    ):
        _record_login_attempt(client_ip)
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
    total_tokens_used = db.query(func.sum(Team.total_tokens_used)).scalar() or 0
    total_budget_usd = db.query(func.sum(Team.budget_usd)).scalar() or 0.0
    total_used_usd = db.query(func.sum(Team.used_usd)).scalar() or 0.0
    
    return AdminStats(
        total_teams=total_teams,
        active_teams=active_teams,
        total_requests=total_requests,
        total_tokens_used=total_tokens_used,
        total_budget_usd=round(total_budget_usd, 2),
        total_used_usd=round(total_used_usd, 6)
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
        remaining_usd = max(0.0, team.budget_usd - team.used_usd)
        usage_percentage = (team.used_usd / team.budget_usd * 100) if team.budget_usd > 0 else 0
        
        result.append(TeamStats(
            id=team.id,
            name=team.name,
            email=team.email,
            token=team.token,
            budget_usd=team.budget_usd,
            used_usd=team.used_usd,
            total_tokens_used=team.total_tokens_used,
            is_active=team.is_active,
            created_at=team.created_at,
            remaining_usd=round(remaining_usd, 6),
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
    remaining_usd = max(0.0, team.budget_usd - team.used_usd)
    usage_percentage = (team.used_usd / team.budget_usd * 100) if team.budget_usd > 0 else 0
    
    return TeamStats(
        id=team.id,
        name=team.name,
        email=team.email,
        token=team.token,
        budget_usd=team.budget_usd,
        used_usd=team.used_usd,
        total_tokens_used=team.total_tokens_used,
        is_active=team.is_active,
        created_at=team.created_at,
        remaining_usd=round(remaining_usd, 6),
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
    existing_team = db.query(Team).filter(Team.name == team_data.name).first()
    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team with name '{team_data.name}' already exists"
        )
    
    if team_data.email:
        existing_email = db.query(Team).filter(Team.email == team_data.email.lower()).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team with email '{team_data.email}' already exists"
            )
    
    token = team_data.token if team_data.token else generate_token()
    
    existing_token = db.query(Team).filter(Team.token == token).first()
    if existing_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token already exists"
        )
    
    team = Team(
        name=team_data.name,
        email=team_data.email.lower() if team_data.email else None,
        token=token,
        budget_usd=team_data.budget_usd,
        max_requests_per_minute=team_data.max_requests_per_minute,
        used_usd=0.0,
        total_tokens_used=0,
        is_active=True,
        created_at=datetime.now()
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
    
    if team_data.name is not None:
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
    
    if team_data.budget_usd is not None:
        team.budget_usd = team_data.budget_usd
    
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
    """Reset team's usage counter (USD spent and tokens used)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found"
        )
    
    team.used_usd = 0.0
    team.total_tokens_used = 0
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
    
    log_files.sort(key=lambda x: x["modified"], reverse=True)
    return log_files


@router.get("/server-logs/{filename}", response_class=PlainTextResponse)
def get_server_log_content(
    filename: str,
    authenticated: bool = Depends(verify_admin_password)
):
    """Get the content of a specific server log file."""
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

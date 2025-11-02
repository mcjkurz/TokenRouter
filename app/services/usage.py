"""Usage tracking service."""
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.database import Team, RequestLog


def log_request(
    db: Session,
    team_id: int,
    model: str,
    input_tokens: int,
    output_tokens: int,
    status: str,
    error_message: str = None,
    request_payload: Optional[Dict[str, Any]] = None,
    response_payload: Optional[Dict[str, Any]] = None
) -> RequestLog:
    """
    Log an API request with full payload data.
    
    Args:
        db: Database session
        team_id: Team ID
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        status: Request status
        error_message: Error message if failed
        request_payload: Full request data (messages, parameters)
        response_payload: Full response data
    
    Returns:
        Created request log
    """
    total_tokens = input_tokens + output_tokens
    
    # Convert payloads to JSON strings
    request_json = json.dumps(request_payload) if request_payload else None
    response_json = json.dumps(response_payload) if response_payload else None
    
    log = RequestLog(
        team_id=team_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        status=status,
        error_message=error_message,
        request_payload=request_json,
        response_payload=response_json
    )
    
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return log


def update_team_usage(db: Session, team_id: int, tokens_used: int) -> None:
    """
    Update team's token usage.
    
    Args:
        db: Database session
        team_id: Team ID
        tokens_used: Number of tokens used
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if team:
        team.used_tokens += tokens_used
        db.commit()


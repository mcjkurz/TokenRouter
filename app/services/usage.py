"""Usage tracking service."""
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import update
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
    response_payload: Optional[Dict[str, Any]] = None,
    tokens_for_quota: Optional[int] = None,
) -> RequestLog:
    """
    Log an API request and optionally update team quota in a single transaction.

    When *tokens_for_quota* is provided (and > 0) the team's ``used_tokens``
    counter is bumped atomically inside the same commit that writes the log
    row — eliminating a second round-trip and keeping the two consistent.
    """
    total_tokens = input_tokens + output_tokens
    model_lower = model.lower()

    request_json = json.dumps(request_payload) if request_payload else None
    response_json = json.dumps(response_payload) if response_payload else None

    local_now = datetime.now()

    log = RequestLog(
        team_id=team_id,
        timestamp=local_now,
        model=model_lower,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        status=status,
        error_message=error_message,
        request_payload=request_json,
        response_payload=response_json,
    )

    db.add(log)

    if tokens_for_quota and tokens_for_quota > 0:
        db.execute(
            update(Team)
            .where(Team.id == team_id)
            .values(used_tokens=Team.used_tokens + tokens_for_quota)
        )

    db.commit()
    db.refresh(log)

    return log


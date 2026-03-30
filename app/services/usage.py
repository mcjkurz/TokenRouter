"""Usage tracking service."""
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import update, and_
from sqlalchemy.orm import Session
from app.models.database import Team, RequestLog
from app.core.config import settings


# Default token reservation for requests where final usage is unknown upfront
DEFAULT_TOKEN_RESERVATION = 50000


def _truncate_json_payload(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    """Serialize payload to JSON and cap stored bytes via configuration."""
    if not payload:
        return None

    payload_json = json.dumps(payload, ensure_ascii=False)
    max_bytes = settings.log_payload_max_bytes
    if max_bytes <= 0:
        return None

    encoded = payload_json.encode("utf-8")
    if len(encoded) <= max_bytes:
        return payload_json

    marker = "...[truncated]"
    marker_bytes = marker.encode("utf-8")
    if max_bytes <= len(marker_bytes):
        return marker[:max_bytes]

    kept = encoded[: max_bytes - len(marker_bytes)]
    kept_text = kept.decode("utf-8", errors="ignore")
    return f"{kept_text}{marker}"


def reserve_quota(db: Session, team_id: int, max_reserve_amount: int = DEFAULT_TOKEN_RESERVATION) -> Tuple[bool, int]:
    """
    Atomically reserve tokens from a team's quota.
    
    Uses a conditional UPDATE to ensure reservation only succeeds when quota
    remains, and adapts the reservation size to the team's remaining quota.
    This prevents race conditions and avoids falsely rejecting requests when
    remaining quota is smaller than the default reservation size.
    
    Args:
        db: Database session
        team_id: Team ID
        max_reserve_amount: Upper bound for reservation (actual may be lower)
    
    Returns:
        Tuple of (success: bool, reserved_amount: int)
        - success=True means tokens were reserved
        - success=False means quota would be exceeded
    """
    # Retry once to handle races where remaining quota changes between read/update.
    for _ in range(2):
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            return False, 0

        remaining = max(0, team.quota_tokens - team.used_tokens)
        if remaining <= 0:
            return False, 0

        reserve_amount = min(max_reserve_amount, remaining)

        result = db.execute(
            update(Team)
            .where(
                and_(
                    Team.id == team_id,
                    Team.used_tokens + reserve_amount <= Team.quota_tokens
                )
            )
            .values(used_tokens=Team.used_tokens + reserve_amount)
        )
        db.commit()

        # rowcount == 1 means the update succeeded (quota check passed)
        if result.rowcount == 1:
            return True, reserve_amount

    return False, 0


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
    reserved_tokens: int = 0,
) -> RequestLog:
    """
    Log an API request and adjust quota based on actual vs reserved tokens.

    When *reserved_tokens* > 0, this adjusts the quota to reflect actual usage:
    - If tokens_for_quota > reserved: charges the difference
    - If tokens_for_quota < reserved: refunds the difference
    - If tokens_for_quota == 0 and reserved > 0: releases the full reservation
    """
    total_tokens = input_tokens + output_tokens
    model_lower = model.lower()

    request_json = _truncate_json_payload(request_payload)
    response_json = _truncate_json_payload(response_payload)

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

    # Adjust quota: actual usage minus what was already reserved
    actual = tokens_for_quota if tokens_for_quota and tokens_for_quota > 0 else 0
    adjustment = actual - reserved_tokens
    if adjustment != 0:
        db.execute(
            update(Team)
            .where(Team.id == team_id)
            .values(used_tokens=Team.used_tokens + adjustment)
        )

    db.commit()
    db.refresh(log)

    return log


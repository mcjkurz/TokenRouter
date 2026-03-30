"""Usage tracking service with USD-based pricing."""
import json
import math
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import update, and_
from sqlalchemy.orm import Session
from app.models.database import Team, RequestLog
from app.core.config import settings
from app.core.providers import provider_config


# Default USD reservation for requests where final cost is unknown upfront
DEFAULT_USD_RESERVATION = 0.05  # $0.05 default reservation


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


def estimate_tokens_from_chars(char_count: int) -> int:
    """Estimate tokens from character count using ~4 chars/token."""
    if char_count <= 0:
        return 0
    return math.ceil(char_count / 4)


def estimate_tokens_from_payload(payload: Optional[Dict[str, Any]]) -> int:
    """
    Estimate input tokens by collecting string fields from payload.

    This is intentionally simple and provider-agnostic for fallback charging.
    """
    if not payload:
        return 0

    chunks = []

    def _walk(value: Any) -> None:
        if isinstance(value, str):
            if value:
                chunks.append(value)
            return
        if isinstance(value, list):
            for item in value:
                _walk(item)
            return
        if isinstance(value, dict):
            for nested in value.values():
                _walk(nested)

    _walk(payload)
    return estimate_tokens_from_chars(sum(len(part) for part in chunks))


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate USD cost based on model-specific or provider pricing.
    
    Pricing priority:
    1. Model-specific pricing (if defined for the exact model or matching pattern)
    2. Provider default pricing
    3. Global default pricing (from config.pricing)
    
    Args:
        model: Model name (used to find provider and pricing)
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
    
    Returns:
        Cost in USD (float)
    """
    provider = provider_config.get_provider_for_model(model)
    
    if provider:
        # Get model-specific pricing or provider default
        input_rate, output_rate = provider.get_pricing_for_model(model)
    else:
        # Fall back to global default pricing
        input_rate = settings.pricing.default_input_per_million
        output_rate = settings.pricing.default_output_per_million
    
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


def reserve_budget(
    db: Session, 
    team_id: int, 
    max_reserve_usd: float = DEFAULT_USD_RESERVATION
) -> Tuple[bool, float]:
    """
    Atomically reserve USD from a team's budget.
    
    Uses a conditional UPDATE to ensure reservation only succeeds when budget
    remains, and adapts the reservation size to the team's remaining budget.
    This prevents race conditions and avoids falsely rejecting requests when
    remaining budget is smaller than the default reservation size.
    
    Args:
        db: Database session
        team_id: Team ID
        max_reserve_usd: Upper bound for reservation in USD (actual may be lower)
    
    Returns:
        Tuple of (success: bool, reserved_usd: float)
        - success=True means USD was reserved
        - success=False means budget would be exceeded
    """
    for _ in range(2):
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            return False, 0.0

        remaining = max(0.0, team.budget_usd - team.used_usd)
        if remaining <= 0:
            return False, 0.0

        reserve_amount = min(max_reserve_usd, remaining)

        result = db.execute(
            update(Team)
            .where(
                and_(
                    Team.id == team_id,
                    Team.used_usd + reserve_amount <= Team.budget_usd
                )
            )
            .values(used_usd=Team.used_usd + reserve_amount)
        )
        db.commit()

        if result.rowcount == 1:
            return True, reserve_amount

    return False, 0.0


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
    cost_usd: Optional[float] = None,
    reserved_usd: float = 0.0,
) -> RequestLog:
    """
    Log an API request and adjust budget based on actual vs reserved USD.

    When *reserved_usd* > 0, this adjusts the budget to reflect actual cost:
    - If cost_usd > reserved: charges the difference
    - If cost_usd < reserved: refunds the difference
    - If cost_usd == 0 and reserved > 0: releases the full reservation
    
    Also updates the team's total_tokens_used for statistics.
    """
    total_tokens = input_tokens + output_tokens
    model_lower = model.lower()

    # Calculate cost if not provided
    if cost_usd is None:
        cost_usd = calculate_cost(model, input_tokens, output_tokens)

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
        cost_usd=cost_usd,
        status=status,
        error_message=error_message,
        request_payload=request_json,
        response_payload=response_json,
    )

    db.add(log)

    # Adjust budget: actual cost minus what was already reserved
    actual_cost = cost_usd if cost_usd and cost_usd > 0 else 0.0
    adjustment = actual_cost - reserved_usd
    
    # Build update values - always update token count for successful requests
    update_values = {}
    if adjustment != 0:
        update_values["used_usd"] = Team.used_usd + adjustment
    
    # Update token count for stats (only for successful requests with tokens)
    if total_tokens > 0 and status == "success":
        update_values["total_tokens_used"] = Team.total_tokens_used + total_tokens
    
    if update_values:
        db.execute(
            update(Team)
            .where(Team.id == team_id)
            .values(**update_values)
        )

    db.commit()
    db.refresh(log)

    return log

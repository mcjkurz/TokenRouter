"""Proxy API endpoints — transparent passthrough to upstream providers."""
import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import validate_team_token, check_quota, check_rate_limit
from app.core.providers import provider_config
from app.models.database import Team
from app.services.proxy import proxy_service
from app.services.usage import log_request, update_team_usage

logger = logging.getLogger("uvicorn.error")
router = APIRouter()


@router.get("/v1/models")
async def list_models():
    """List available model patterns from all providers. No auth required."""
    return provider_config.get_all_model_names()


@router.get("/v1/usage/{username}")
async def get_usage(username: str, db: Session = Depends(get_db)):
    """Get usage/quota for a user. No auth required."""
    team = db.query(Team).filter(Team.name.ilike(username)).first()
    if not team:
        return {}

    from app.models.database import RequestLog
    total_requests = db.query(RequestLog).filter(RequestLog.team_id == team.id).count()
    remaining = team.quota_tokens - team.used_tokens

    return {
        "team_name": team.name,
        "quota_tokens": team.quota_tokens,
        "used_tokens": team.used_tokens,
        "remaining_tokens": remaining,
        "usage_percentage": round((team.used_tokens / team.quota_tokens * 100) if team.quota_tokens else 0, 2),
        "total_requests": total_requests,
        "max_requests_per_minute": team.max_requests_per_minute,
        "is_active": team.is_active,
    }


# ── shared proxy logic ──────────────────────────────────────────

async def _proxy(request: Request, team: Team, db: Session, endpoint: str):
    """
    Transparent passthrough.
    
    Reads the raw JSON body, validates auth/quota/model,
    then forwards the entire payload as-is to the upstream provider.
    """
    check_rate_limit(team)
    check_quota(team)

    payload: Dict[str, Any] = await request.json()
    model = provider_config.resolve_model(payload.get("model", ""))
    payload["model"] = model
    is_stream = payload.get("stream", False)

    logger.info(f"[api] {model} stream={is_stream} -> /{endpoint}")

    if not provider_config.is_model_allowed(model):
        error_msg = f"Model '{model}' not available. See GET /v1/models"
        log_request(db, team.id, model, 0, 0, "error", error_msg, request_payload=payload)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_msg)

    try:
        if is_stream:
            log_request(db, team.id, model, 0, 0, "streaming", request_payload=payload)
            return StreamingResponse(
                proxy_service.forward_stream(payload, endpoint),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

        response_data = await proxy_service.forward(payload, endpoint)

        usage = response_data.get("usage", {})
        inp = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
        out = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
        total = usage.get("total_tokens", 0) or (inp + out)

        log_request(db, team.id, model, inp, out, "success",
                    request_payload=payload, response_payload=response_data)
        update_team_usage(db, team.id, total)
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        log_request(db, team.id, model, 0, 0, "error", str(e), request_payload=payload)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error: {e}")


# ── endpoints ────────────────────────────────────────────────────

@router.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    team: Team = Depends(validate_team_token),
    db: Session = Depends(get_db),
):
    """Chat completions passthrough."""
    return await _proxy(request, team, db, "chat/completions")


@router.post("/v1/responses")
async def responses(
    request: Request,
    team: Team = Depends(validate_team_token),
    db: Session = Depends(get_db),
):
    """OpenAI Responses API passthrough."""
    return await _proxy(request, team, db, "responses")

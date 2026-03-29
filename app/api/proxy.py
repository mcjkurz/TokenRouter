"""Proxy API endpoint for chat completions."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import validate_team_token, check_quota, check_rate_limit
from app.core.providers import provider_config
from app.models.database import Team
from app.models.schemas import ChatCompletionRequest, ChatCompletionResponse
from app.services.proxy import proxy_service
from app.services.usage import log_request, update_team_usage

router = APIRouter()


@router.get("/v1/models")
async def list_models():
    """
    List available models.
    
    Returns all model patterns from all configured providers.
    No authentication required.
    """
    return provider_config.get_all_model_names()


@router.get("/v1/usage/{username}")
async def get_usage(
    username: str,
    db: Session = Depends(get_db)
):
    """
    Get current usage and quota information for a team by username.
    
    No authentication required. Returns empty response if team doesn't exist.
    This endpoint does not consume tokens - it's for checking your quota.
    """
    team = db.query(Team).filter(Team.name.ilike(username)).first()
    
    if not team:
        return {}
    
    remaining = team.quota_tokens - team.used_tokens
    usage_percentage = (team.used_tokens / team.quota_tokens * 100) if team.quota_tokens > 0 else 0
    
    from app.models.database import RequestLog
    total_requests = db.query(RequestLog).filter(RequestLog.team_id == team.id).count()
    
    return {
        "team_name": team.name,
        "quota_tokens": team.quota_tokens,
        "used_tokens": team.used_tokens,
        "remaining_tokens": remaining,
        "usage_percentage": round(usage_percentage, 2),
        "total_requests": total_requests,
        "max_requests_per_minute": team.max_requests_per_minute,
        "is_active": team.is_active
    }


@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    team: Team = Depends(validate_team_token),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint for chat completions.
    
    Validates team token, checks quota, routes request to appropriate provider,
    and tracks usage.
    """
    check_rate_limit(team)
    check_quota(team)
    
    model_lower = request.model.lower()
    
    if not provider_config.is_model_allowed(request.model):
        available_models = ', '.join(provider_config.get_all_model_names())
        error_msg = (
            f"Model '{request.model}' is not available. "
            f"Available models: {available_models}. "
            f"You can also list models at GET /v1/models"
        )
        request_data = request.model_dump(exclude_none=True)
        request_data["model"] = model_lower
        log_request(
            db, team.id, model_lower, 0, 0, "error", error_msg,
            request_payload=request_data
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    try:
        if request.stream:
            payload = request.model_dump(exclude_none=True)
            payload["model"] = model_lower
            
            log_request(
                db, team.id, model_lower, 0, 0, "streaming",
                request_payload=payload
            )
            
            return StreamingResponse(
                proxy_service.forward_chat_completion_stream(payload),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        
        payload = request.model_dump(exclude_none=True)
        payload["model"] = model_lower
        response_data = await proxy_service.forward_chat_completion(payload)
        
        usage = response_data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        log_request(
            db, team.id, model_lower,
            input_tokens, output_tokens, "success",
            request_payload=payload,
            response_payload=response_data
        )
        
        update_team_usage(db, team.id, total_tokens)
        
        return response_data
    
    except HTTPException as e:
        request_data = request.model_dump(exclude_none=True)
        request_data["model"] = model_lower
        log_request(
            db, team.id, model_lower, 0, 0, "error",
            str(e.detail),
            request_payload=request_data
        )
        raise
    
    except Exception as e:
        request_data = request.model_dump(exclude_none=True)
        request_data["model"] = model_lower
        log_request(
            db, team.id, model_lower, 0, 0, "error",
            str(e),
            request_payload=request_data
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )

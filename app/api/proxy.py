"""Proxy API endpoint for chat completions."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import validate_team_token, check_quota
from app.core.config import settings
from app.models.database import Team
from app.models.schemas import ChatCompletionRequest, ChatCompletionResponse
from app.services.proxy import proxy_service
from app.services.usage import log_request, update_team_usage

router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    team: Team = Depends(validate_team_token),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint for chat completions.
    
    Validates team token, checks quota, forwards request to provider,
    and tracks usage.
    """
    # Check quota before processing
    check_quota(team)
    
    # Validate model
    if request.model not in settings.allowed_models_list:
        log_request(
            db, team.id, request.model, 0, 0, "error",
            f"Model '{request.model}' not allowed. Allowed models: {', '.join(settings.allowed_models_list)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{request.model}' not allowed. Allowed models: {', '.join(settings.allowed_models_list)}"
        )
    
    # Streaming not supported in this simple implementation
    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming is not supported"
        )
    
    try:
        # Forward request to provider
        payload = request.model_dump(exclude_none=True)
        response_data = await proxy_service.forward_chat_completion(payload)
        
        # Extract token usage from response
        usage = response_data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        # Log successful request
        log_request(
            db, team.id, request.model,
            input_tokens, output_tokens, "success"
        )
        
        # Update team usage
        update_team_usage(db, team.id, total_tokens)
        
        return response_data
    
    except HTTPException as e:
        # Log failed request
        log_request(
            db, team.id, request.model, 0, 0, "error",
            str(e.detail)
        )
        raise
    
    except Exception as e:
        # Log unexpected error
        log_request(
            db, team.id, request.model, 0, 0, "error",
            str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


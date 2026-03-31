"""Proxy API endpoints — transparent passthrough to upstream providers."""
import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.core.auth import validate_team_token, check_budget, check_rate_limit
from app.core.providers import provider_config
from app.models.database import Team, RequestLog
from app.services.proxy import proxy_service
from app.services.usage import (
    log_request,
    reserve_budget,
    calculate_cost,
    DEFAULT_USD_RESERVATION,
    estimate_tokens_from_payload,
    estimate_tokens_from_chars,
)

logger = logging.getLogger("uvicorn.error")
router = APIRouter()


def _parse_sse_for_usage(raw_data: bytes) -> tuple[Optional[Dict[str, Any]], int, bool]:
    """
    Parse collected SSE data post-hoc to extract usage info.
    
    Returns:
        (usage_data, output_char_count, error_occurred)
    """
    usage_data: Optional[Dict[str, Any]] = None
    output_char_count = 0
    error_occurred = False
    
    text = raw_data.decode("utf-8", errors="replace").replace("\r\n", "\n")
    
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        
        data_lines = []
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:]
                if data_str.startswith(" "):
                    data_str = data_str[1:]
                data_lines.append(data_str)
        
        if not data_lines:
            continue
        
        payload = "\n".join(data_lines)
        if payload == "[DONE]":
            continue
        
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        
        if not isinstance(event, dict):
            continue
        
        if "usage" in event and event["usage"]:
            usage_data = event["usage"]
        
        choices = event.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            content = delta.get("content", "")
            if isinstance(content, str):
                output_char_count += len(content)
                if content.startswith("[Error]"):
                    error_occurred = True
        
        output_text = event.get("output_text")
        if isinstance(output_text, str):
            output_char_count += len(output_text)
    
    return usage_data, output_char_count, error_occurred


async def _stream_with_usage_tracking(
    generator: AsyncGenerator[bytes, None],
    team_id: int,
    model: str,
    request_payload: Dict[str, Any],
    cancel_event: asyncio.Event,
    reserved_usd: float,
) -> AsyncGenerator[bytes, None]:
    """
    Wrap a streaming response to capture usage from the final chunk.
    
    Yields chunks immediately for minimal latency, then parses the collected
    data post-hoc after the stream completes to extract usage stats.
    """
    collected_chunks: list[bytes] = []
    client_disconnected = False
    
    try:
        async for chunk in generator:
            collected_chunks.append(chunk)
            yield chunk
    except (ConnectionError, asyncio.CancelledError):
        client_disconnected = True
        cancel_event.set()
        logger.info(f"[stream] {model} client disconnected — cancelling upstream")
    
    # Parse usage post-hoc from collected data
    raw_data = b"".join(collected_chunks)
    usage_data, output_char_count, error_occurred = _parse_sse_for_usage(raw_data)
    
    db = SessionLocal()
    try:
        if client_disconnected:
            log_request(db, team_id, model, 0, 0, "cancelled", "Client disconnected",
                        request_payload=request_payload, reserved_usd=reserved_usd)
        elif error_occurred:
            log_request(db, team_id, model, 0, 0, "error", "Streaming error",
                        request_payload=request_payload, reserved_usd=reserved_usd)
        elif usage_data:
            inp = usage_data.get("prompt_tokens", 0) or usage_data.get("input_tokens", 0)
            out = usage_data.get("completion_tokens", 0) or usage_data.get("output_tokens", 0)
            cost = calculate_cost(model, inp, out)
            
            log_request(db, team_id, model, inp, out, "success",
                        request_payload=request_payload, cost_usd=cost,
                        reserved_usd=reserved_usd)
            logger.info(f"[stream] {model} usage: {inp} in, {out} out, ${cost:.6f}")
        else:
            # Fallback: estimate usage and calculate cost
            estimated_input = estimate_tokens_from_payload(request_payload)
            estimated_output = estimate_tokens_from_chars(output_char_count)
            min_tokens = settings.usage_missing_min_charge_tokens
            max_tokens = settings.usage_missing_charge_max_effective
            
            clamped_input = max(min_tokens // 2, min(estimated_input, max_tokens // 2))
            clamped_output = max(min_tokens // 2, min(estimated_output, max_tokens // 2))
            estimated_cost = calculate_cost(model, clamped_input, clamped_output)
            
            # Cap estimated cost at reserved amount
            final_cost = min(estimated_cost, reserved_usd)
            
            log_request(
                db, team_id, model,
                clamped_input, clamped_output,
                "usage_missing_estimated",
                f"Provider stream completed without usage; charged ${final_cost:.6f}",
                request_payload=request_payload,
                cost_usd=final_cost,
                reserved_usd=reserved_usd,
            )
            logger.warning(
                f"[stream] {model} missing usage; estimated {clamped_input} in + "
                f"{clamped_output} out -> charged ${final_cost:.6f}"
            )
    finally:
        db.close()


@router.get("/v1/models")
async def list_models():
    """List available models in OpenAI-compatible format. No auth required."""
    models_with_providers = provider_config.get_all_models_with_providers()
    return {
        "object": "list",
        "data": [
            {"id": m, "object": "model", "created": 0, "owned_by": provider}
            for m, provider in models_with_providers
        ]
    }


@router.get("/v1/usage/{api_key}")
async def get_usage_by_key(api_key: str, db: Session = Depends(get_db)):
    """
    Get usage/budget for a team by API key. No auth required.
    """
    team = db.query(Team).filter(Team.token == api_key).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found for the provided API key"
        )

    total_requests = db.query(RequestLog).filter(RequestLog.team_id == team.id).count()

    return {
        "team_name": team.name,
        "budget_usd": round(team.budget_usd, 2),
        "used_usd": round(team.used_usd, 6),
        "remaining_usd": round(team.remaining_usd, 6),
        "total_tokens_used": team.total_tokens_used,
        "total_requests": total_requests,
        "is_active": team.is_active,
    }


# ── shared proxy logic ──────────────────────────────────────────

async def _proxy(request: Request, team: Team, db: Session, endpoint: str):
    """
    Transparent passthrough.
    
    Reads the raw JSON body, validates auth/budget/model,
    then forwards the entire payload as-is to the upstream provider.
    
    Uses atomic budget reservation to prevent concurrent requests from
    exceeding budget limits.
    """
    check_rate_limit(team)
    check_budget(team)  # Fast pre-check (actual enforcement via reserve_budget)

    try:
        payload: Dict[str, Any] = await request.json()
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON in request body: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse request body: {e}"
        )

    model = provider_config.resolve_model(payload.get("model", ""))
    payload["model"] = model
    is_stream = payload.get("stream", False)

    logger.info(f"[api] {model} stream={is_stream} -> /{endpoint}")

    if not provider_config.is_model_allowed(model):
        error_msg = f"Model '{model}' not available. See GET /v1/models"
        log_request(db, team.id, model, 0, 0, "error", error_msg, request_payload=payload)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # Atomically reserve budget before making the request
    reserved_ok, reserved_usd = reserve_budget(db, team.id, DEFAULT_USD_RESERVATION)
    if not reserved_ok:
        error_msg = (
            f"Budget exceeded. "
            f"Remaining: ${team.remaining_usd:.2f}. "
            f"Check your usage at GET /v1/usage/{team.token}"
        )
        log_request(db, team.id, model, 0, 0, "budget_exceeded", error_msg, request_payload=payload)
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=error_msg)

    try:
        if is_stream:
            if "stream_options" not in payload:
                payload["stream_options"] = {"include_usage": True}
            elif isinstance(payload.get("stream_options"), dict):
                payload["stream_options"]["include_usage"] = True
            
            cancel_event = asyncio.Event()
            
            return StreamingResponse(
                _stream_with_usage_tracking(
                    proxy_service.forward_stream(payload, endpoint, cancel_event),
                    team.id, model, payload, cancel_event, reserved_usd,
                ),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

        response_data = await proxy_service.forward(payload, endpoint)

        usage = response_data.get("usage", {})
        inp = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
        out = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
        cost = calculate_cost(model, inp, out)

        log_request(db, team.id, model, inp, out, "success",
                    request_payload=payload, response_payload=response_data,
                    cost_usd=cost, reserved_usd=reserved_usd)
        return response_data

    except HTTPException:
        log_request(db, team.id, model, 0, 0, "error", "HTTP error",
                    request_payload=payload, reserved_usd=reserved_usd)
        raise
    except Exception as e:
        log_request(db, team.id, model, 0, 0, "error", str(e),
                    request_payload=payload, reserved_usd=reserved_usd)
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


@router.post("/v1/completions")
async def completions(
    request: Request,
    team: Team = Depends(validate_team_token),
    db: Session = Depends(get_db),
):
    """Legacy completions passthrough (used by autocomplete clients like Continue)."""
    return await _proxy(request, team, db, "completions")


@router.post("/v1/responses")
async def responses(
    request: Request,
    team: Team = Depends(validate_team_token),
    db: Session = Depends(get_db),
):
    """OpenAI Responses API passthrough."""
    return await _proxy(request, team, db, "responses")

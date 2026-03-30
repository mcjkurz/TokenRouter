"""Proxy service — forwards requests to upstream LLM providers."""
import asyncio
import httpx
import json
import logging
import uuid
import time
from typing import Dict, Any, AsyncGenerator
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.providers import provider_config, Provider

logger = logging.getLogger("uvicorn.error")


def _create_error_chunk(message: str, model: str = "error") -> bytes:
    """Build an SSE chunk that surfaces an error as assistant text."""
    chunk = {
        "id": f"chatcmpl-err-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"role": "assistant", "content": f"[Error] {message}"},
            "finish_reason": "stop",
        }],
    }
    return f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n".encode()


def _resolve(payload: Dict[str, Any]) -> Provider:
    """Look up the provider for the model in *payload*."""
    model = payload.get("model", "")
    provider = provider_config.get_provider_for_model(model)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No provider configured for model '{model}'",
        )
    return provider


def _headers(provider: Provider) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if provider.api_key:
        h["Authorization"] = f"Bearer {provider.api_key}"
    return h


class ProxyService:
    def __init__(self):
        self.timeout = settings.provider_timeout
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self):
        await self._client.aclose()

    # ── streaming ────────────────────────────────────────────────

    async def forward_stream(
        self,
        payload: Dict[str, Any],
        endpoint: str,
        cancel_event: asyncio.Event,
    ) -> AsyncGenerator[bytes, None]:
        provider = _resolve(payload)
        url = f"{provider.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        model = payload.get("model", "")

        logger.info(f"[stream] {model} -> {provider.name} /{endpoint}")

        try:
            async with self._client.stream("POST", url, json=payload, headers=_headers(provider)) as resp:
                if resp.status_code != 200:
                    body = (await resp.aread()).decode()
                    try:
                        body = json.loads(body).get("error", {}).get("message", body)
                    except Exception:
                        pass
                    msg = f"Provider '{provider.name}' returned {resp.status_code}: {body}"
                    logger.error(f"[stream] {msg}")
                    yield _create_error_chunk(msg, model)
                    return

                chunks = 0
                async for chunk in resp.aiter_bytes():
                    if cancel_event.is_set():
                        logger.info(f"[stream] {model} cancelled by client after {chunks} chunks")
                        await resp.aclose()
                        return
                    chunks += 1
                    yield chunk
                logger.info(f"[stream] {model} done — {chunks} chunks")

        except httpx.TimeoutException:
            msg = f"Provider '{provider.name}' timed out"
            logger.error(f"[stream] {msg}")
            yield _create_error_chunk(msg, model)
        except httpx.RequestError as e:
            msg = f"Cannot reach provider '{provider.name}': {e}"
            logger.error(f"[stream] {msg}")
            yield _create_error_chunk(msg, model)
        except HTTPException:
            raise
        except Exception as e:
            msg = f"Unexpected error: {e}"
            logger.error(f"[stream] {msg}")
            yield _create_error_chunk(msg, model)

    # ── non-streaming ────────────────────────────────────────────

    async def forward(
        self, payload: Dict[str, Any], endpoint: str
    ) -> Dict[str, Any]:
        provider = _resolve(payload)
        url = f"{provider.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        model = payload.get("model", "")

        logger.info(f"[request] {model} -> {provider.name} /{endpoint}")

        try:
            resp = await self._client.post(url, json=payload, headers=_headers(provider))

            if resp.status_code != 200:
                detail = resp.text
                try:
                    detail = resp.json().get("error", {}).get("message", detail)
                except Exception:
                    pass
                logger.error(f"[request] {provider.name} returned {resp.status_code}: {detail}")
                raise HTTPException(status_code=resp.status_code, detail=f"Provider error: {detail}")

            return resp.json()

        except httpx.TimeoutException:
            raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, detail=f"Provider '{provider.name}' timed out")
        except httpx.RequestError as e:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Cannot reach provider '{provider.name}': {e}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {e}")


proxy_service = ProxyService()

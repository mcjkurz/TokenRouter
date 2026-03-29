"""Proxy service for forwarding requests to LLM providers."""
import httpx
import json
from typing import Dict, Any, AsyncGenerator, Optional
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.providers import provider_config, Provider


class ProxyService:
    """Service for proxying requests to LLM providers based on model routing."""
    
    def __init__(self):
        self.timeout = settings.provider_timeout
    
    def _get_provider_for_model(self, model: str) -> Provider:
        """Get the provider that handles this model."""
        provider = provider_config.get_provider_for_model(model)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No provider configured for model '{model}'"
            )
        return provider
    
    async def forward_chat_completion_stream(
        self, payload: Dict[str, Any]
    ) -> AsyncGenerator[bytes, None]:
        """
        Forward streaming chat completion request to the appropriate provider.
        
        Yields raw SSE chunks from the provider.
        """
        model = payload.get("model", "")
        provider = self._get_provider_for_model(model)
        
        headers = {
            "Content-Type": "application/json"
        }
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"
        
        url = f"{provider.base_url.rstrip('/')}/chat/completions"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        error_detail = error_text.decode()
                        try:
                            error_json = json.loads(error_detail)
                            error_detail = error_json.get("error", {}).get("message", error_detail)
                        except:
                            pass
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Provider '{provider.name}' error: {error_detail}"
                        )
                    
                    async for chunk in response.aiter_bytes():
                        yield chunk
        
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Request to provider '{provider.name}' timed out"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error connecting to provider '{provider.name}': {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}"
            )
    
    async def forward_chat_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Forward chat completion request to the appropriate provider.
        
        Args:
            payload: Request payload including 'model' field
        
        Returns:
            Provider response
        
        Raises:
            HTTPException: If request fails
        """
        model = payload.get("model", "")
        provider = self._get_provider_for_model(model)
        
        headers = {
            "Content-Type": "application/json"
        }
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"
        
        url = f"{provider.base_url.rstrip('/')}/chat/completions"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("error", {}).get("message", error_detail)
                    except:
                        pass
                    
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Provider '{provider.name}' error: {error_detail}"
                    )
                
                return response.json()
        
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Request to provider '{provider.name}' timed out"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error connecting to provider '{provider.name}': {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}"
            )


proxy_service = ProxyService()

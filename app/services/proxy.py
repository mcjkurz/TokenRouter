"""Proxy service for forwarding requests to LLM provider."""
import httpx
from typing import Dict, Any
from fastapi import HTTPException, status

from app.core.config import settings


class ProxyService:
    """Service for proxying requests to LLM provider."""
    
    def __init__(self):
        self.base_url = settings.provider_base_url
        self.api_key = settings.provider_api_key
        self.timeout = 120.0  # 2 minutes timeout
    
    async def forward_chat_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Forward chat completion request to provider.
        
        Args:
            payload: Request payload
        
        Returns:
            Provider response
        
        Raises:
            HTTPException: If request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        
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
                        detail=f"Provider error: {error_detail}"
                    )
                
                return response.json()
        
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request to provider timed out"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error connecting to provider: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}"
            )


proxy_service = ProxyService()


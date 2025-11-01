"""Configuration management."""
import os
import sys
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Set your provider API key here or via PROVIDER_API_KEY environment variable
    provider_api_key: str = Field(default=os.getenv("PROVIDER_API_KEY", ""))
    provider_base_url: str = Field(default=os.getenv("PROVIDER_BASE_URL", "https://api.poe.com/v1"))
    default_model: str = Field(default=os.getenv("DEFAULT_MODEL", "GPT-5-nano"))
    allowed_models: str = Field(default=os.getenv("ALLOWED_MODELS", "GPT-5-nano,GPT-5-mini,Gemini-2.5-flash,Gemini-2.5-pro"))
    database_url: str = Field(default=os.getenv("DATABASE_URL", "sqlite:///./data/tokenrouter.db"))
    host: str = Field(default=os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default=int(os.getenv("PORT", "8000")))
    admin_password: str = Field(default=os.getenv("ADMIN_PASSWORD", "admin123"))
    
    class Config:
        case_sensitive = False
    
    @property
    def allowed_models_list(self) -> List[str]:
        """Parse allowed models from comma-separated string."""
        return [m.strip() for m in self.allowed_models.split(",") if m.strip()]
    
    def validate_api_key(self) -> None:
        """Check if API key is provided."""
        if not self.provider_api_key:
            print("\n" + "="*60)
            print("⚠️  ERROR: Provider API key not configured!")
            print("="*60)
            print("\nPlease set your API key in one of these ways:")
            print("  1. Environment variable: export PROVIDER_API_KEY='your-key-here'")
            print("  2. Edit app/core/config.py and set provider_api_key directly")
            print("\nExample:")
            print("  export PROVIDER_API_KEY='pk-xxxxx'")
            print("  python run.py")
            print("="*60 + "\n")
            sys.exit(1)


settings = Settings()


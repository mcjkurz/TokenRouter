"""Configuration management."""
import os
import sys
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    provider_api_key: str = Field(default=os.getenv("PROVIDER_API_KEY", ""))
    provider_base_url: str = Field(default=os.getenv("PROVIDER_BASE_URL", ""))
    provider_timeout: float = Field(default=float(os.getenv("PROVIDER_TIMEOUT", "120.0")))
    default_model: str = Field(default=os.getenv("DEFAULT_MODEL", "GPT-5-nano"))
    allowed_models: str = Field(default=os.getenv("ALLOWED_MODELS", "GPT-5-nano,GPT-5-mini,Gemini-2.5-flash,Gemini-2.5-pro"))
    database_url: str = Field(default=os.getenv("DATABASE_URL", "sqlite:///./data/tokenrouter.db"))
    host: str = Field(default=os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default=int(os.getenv("PORT", "8000")))
    admin_password: str = Field(default=os.getenv("ADMIN_PASSWORD", ""))
    
    class Config:
        case_sensitive = False
    
    @property
    def allowed_models_list(self) -> List[str]:
        """Parse allowed models from comma-separated string."""
        return [m.strip() for m in self.allowed_models.split(",") if m.strip()]
    
    def validate_required_settings(self) -> None:
        """Check if all required settings are provided."""
        missing = []
        
        if not self.provider_api_key:
            missing.append("PROVIDER_API_KEY")
        
        if not self.provider_base_url:
            missing.append("PROVIDER_BASE_URL")
        
        if not self.admin_password:
            missing.append("ADMIN_PASSWORD")
        
        if missing:
            print("\n" + "="*60)
            print("⚠️  ERROR: Required environment variables not set!")
            print("="*60)
            print(f"\nMissing variables: {', '.join(missing)}")
            print("\nYou must set these environment variables before starting the app:")
            print("\nExample:")
            print("  export PROVIDER_API_KEY='your-api-key-here'")
            print("  export PROVIDER_BASE_URL='https://api.poe.com/v1'")
            print("  export ADMIN_PASSWORD='your-secure-password'")
            print("  python run.py")
            print("\nOr set them all at once:")
            print("  export PROVIDER_API_KEY='your-key' PROVIDER_BASE_URL='https://api.poe.com/v1' ADMIN_PASSWORD='your-password'")
            print("  python run.py")
            print("="*60 + "\n")
            sys.exit(1)


settings = Settings()


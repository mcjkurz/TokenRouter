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
    allowed_models: str = Field(default=os.getenv("ALLOWED_MODELS", "GPT-5.1,GPT-5.1-Instant,GPT-5-nano,GPT-5-mini,GPT-5,Gemini-2.5-Flash,Gemini-2.5-Pro,Claude-Haiku-4.5,Claude-Sonnet-4.5,DeepSeek-R1,DeepSeek-V3.2"))
    database_url: str = Field(default=os.getenv("DATABASE_URL", "sqlite:///./data/tokenrouter.db"))
    host: str = Field(default=os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default=int(os.getenv("PORT", "8000")))
    admin_password: str = Field(default=os.getenv("ADMIN_PASSWORD", ""))
    
    # Registration settings
    registration_enabled: bool = Field(default=os.getenv("REGISTRATION_ENABLED", "true").lower() == "true")
    registration_access_codes: str = Field(default=os.getenv("REGISTRATION_ACCESS_CODES", ""))
    allowed_email_domains: str = Field(default=os.getenv("ALLOWED_EMAIL_DOMAINS", "ln.hk,ln.edu.hk"))
    default_registration_quota: int = Field(default=int(os.getenv("DEFAULT_REGISTRATION_QUOTA", "500000")))
    public_api_url: str = Field(default=os.getenv("PUBLIC_API_URL", ""))
    
    # API Documentation settings
    enable_api_docs: bool = Field(default=os.getenv("ENABLE_API_DOCS", "false").lower() == "true")
    
    class Config:
        case_sensitive = False
    
    @property
    def allowed_models_list(self) -> List[str]:
        """Parse allowed models from comma-separated string.
        
        Returns models in their original casing for display purposes.
        """
        return [m.strip() for m in self.allowed_models.split(",") if m.strip()]
    
    @property
    def allowed_models_lowercase(self) -> List[str]:
        """Get lowercase versions of allowed models for case-insensitive comparison."""
        return [m.lower() for m in self.allowed_models_list]
    
    def is_model_allowed(self, model: str) -> bool:
        """Check if a model is allowed (case-insensitive)."""
        return model.lower() in self.allowed_models_lowercase
    
    @property
    def allowed_email_domains_list(self) -> List[str]:
        """Parse allowed email domains from comma-separated string."""
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]
    
    def is_email_domain_allowed(self, email: str) -> bool:
        """Check if an email domain is allowed."""
        email_lower = email.lower()
        return any(email_lower.endswith(f"@{domain}") for domain in self.allowed_email_domains_list)
    
    @property
    def registration_access_codes_list(self) -> List[str]:
        """Parse registration access codes from comma-separated string."""
        return [c.strip() for c in self.registration_access_codes.split(",") if c.strip()]
    
    def is_registration_access_code_valid(self, access_code: str) -> bool:
        """Check if a registration access code is valid."""
        return access_code in self.registration_access_codes_list
    
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


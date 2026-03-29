"""Configuration management."""
import sys
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    provider_api_key: str = Field(default="")
    provider_base_url: str = Field(default="")
    provider_timeout: float = Field(default=120.0)
    default_model: str = Field(default="GPT-5-nano")
    allowed_models: str = Field(default="GPT-5.1,GPT-5.1-Instant,GPT-5-nano,GPT-5-mini,GPT-5,Gemini-2.5-Flash,Gemini-2.5-Pro,Claude-Haiku-4.5,Claude-Sonnet-4.5,DeepSeek-R1,DeepSeek-V3.2,qwen3-coder-next:latest")
    database_url: str = Field(default="sqlite:///./data/tokenrouter.db")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    admin_password: str = Field(default="")
    
    registration_enabled: bool = Field(default=True)
    registration_access_codes: str = Field(default="")
    allowed_email_domains: str = Field(default="ln.hk,ln.edu.hk")
    default_registration_quota: int = Field(default=500000)
    public_api_url: str = Field(default="")
    
    enable_api_docs: bool = Field(default=False)
    
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
            print("  ERROR: Required configuration not set!")
            print("="*60)
            print(f"\nMissing variables: {', '.join(missing)}")
            print("\nTo configure the application:")
            print("\n1. Copy .env.example to .env:")
            print("   cp .env.example .env")
            print("\n2. Edit .env and fill in your values:")
            print("   PROVIDER_API_KEY=your-api-key-here")
            print("   PROVIDER_BASE_URL=https://api.poe.com/v1")
            print("   ADMIN_PASSWORD=your-secure-password")
            print("\n3. Start the application:")
            print("   python run.py")
            print("="*60 + "\n")
            sys.exit(1)


settings = Settings()


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
    
    # Provider settings (now optional - providers.json is the source of truth)
    provider_timeout: float = Field(default=120.0)
    default_model: str = Field(default="gpt-4o")
    
    # Server settings
    database_url: str = Field(default="sqlite:///./data/tokenrouter.db")
    admin_password: str = Field(default="")
    
    # Registration settings
    registration_enabled: bool = Field(default=True)
    registration_access_codes: str = Field(default="")
    allowed_email_domains: str = Field(default="ln.hk,ln.edu.hk")
    default_registration_quota: int = Field(default=500000)
    public_api_url: str = Field(default="")
    
    # API documentation
    enable_api_docs: bool = Field(default=False)

    # Logging
    log_payload_max_bytes: int = Field(default=8192, ge=0)

    # Fallback charging when provider stream usage is missing
    usage_missing_min_charge_tokens: int = Field(default=200, ge=0)
    usage_missing_max_charge_tokens: int = Field(default=4000, ge=0)

    @property
    def usage_missing_charge_max_effective(self) -> int:
        """Ensure effective max is always >= min."""
        return max(self.usage_missing_max_charge_tokens, self.usage_missing_min_charge_tokens)
    
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
            print("   ADMIN_PASSWORD=your-secure-password")
            print("\n3. Configure providers in providers.json:")
            print("   cp providers.example.json providers.json")
            print("\n4. Start the application:")
            print("   python run.py")
            print("="*60 + "\n")
            sys.exit(1)


settings = Settings()

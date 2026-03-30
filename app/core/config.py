"""Configuration management - loads from config.json."""
import json
import sys
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class RegistrationConfig:
    enabled: bool = True
    access_codes: List[str] = field(default_factory=list)
    allowed_email_domains: List[str] = field(default_factory=list)
    default_budget_usd: float = 5.0


@dataclass
class ServerConfig:
    public_api_url: str = ""
    default_model: str = "default-model"
    provider_timeout: float = 120.0
    log_payload_max_bytes: int = 8192


@dataclass
class PricingConfig:
    default_input_per_million: float = 1.0
    default_output_per_million: float = 3.0
    fallback_min_charge_tokens: int = 200
    fallback_max_charge_tokens: int = 4000

    @property
    def fallback_max_charge_tokens_effective(self) -> int:
        """Ensure effective max is always >= min."""
        return max(self.fallback_max_charge_tokens, self.fallback_min_charge_tokens)


@dataclass
class Settings:
    """Application settings loaded from config.json."""
    
    admin_password: str = ""
    registration: RegistrationConfig = field(default_factory=RegistrationConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    pricing: PricingConfig = field(default_factory=PricingConfig)
    
    # Database URL (not in config.json, kept as hardcoded default)
    database_url: str = "sqlite:///./data/tokenrouter.db"
    
    # API documentation (not in config.json)
    enable_api_docs: bool = False
    
    # --- Legacy property aliases for backward compatibility ---
    
    @property
    def provider_timeout(self) -> float:
        return self.server.provider_timeout
    
    @property
    def default_model(self) -> str:
        return self.server.default_model
    
    @property
    def public_api_url(self) -> str:
        return self.server.public_api_url
    
    @property
    def log_payload_max_bytes(self) -> int:
        return self.server.log_payload_max_bytes
    
    @property
    def registration_enabled(self) -> bool:
        return self.registration.enabled
    
    @property
    def default_budget_usd(self) -> float:
        return self.registration.default_budget_usd
    
    @property
    def usage_missing_min_charge_tokens(self) -> int:
        return self.pricing.fallback_min_charge_tokens
    
    @property
    def usage_missing_max_charge_tokens(self) -> int:
        return self.pricing.fallback_max_charge_tokens
    
    @property
    def usage_missing_charge_max_effective(self) -> int:
        return self.pricing.fallback_max_charge_tokens_effective
    
    @property
    def allowed_email_domains_list(self) -> List[str]:
        return [d.lower() for d in self.registration.allowed_email_domains]
    
    def is_email_domain_allowed(self, email: str) -> bool:
        """Check if an email domain is allowed."""
        email_lower = email.lower()
        if not self.allowed_email_domains_list:
            return True
        return any(email_lower.endswith(f"@{domain}") for domain in self.allowed_email_domains_list)
    
    @property
    def registration_access_codes_list(self) -> List[str]:
        return self.registration.access_codes
    
    def is_registration_access_code_valid(self, access_code: str) -> bool:
        """Check if a registration access code is valid."""
        return access_code in self.registration_access_codes_list


def _load_config_file(config_path: str = "config.json") -> dict:
    """Load and return the raw config.json data."""
    path = Path(config_path)
    
    if not path.exists():
        print("\n" + "=" * 60)
        print("  ERROR: config.json not found!")
        print("=" * 60)
        print("\nTo configure the application:")
        print("\n1. Copy config.example.json to config.json:")
        print("   cp config.example.json config.json")
        print("\n2. Edit config.json and fill in your values")
        print("\n3. Start the application:")
        print("   python run.py")
        print("=" * 60 + "\n")
        sys.exit(1)
    
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"\n  ERROR: Invalid JSON in {config_path}: {e}\n")
        sys.exit(1)


def _parse_settings(data: dict) -> Settings:
    """Parse raw config data into Settings object."""
    # Parse registration config
    reg_data = data.get("registration", {})
    registration = RegistrationConfig(
        enabled=reg_data.get("enabled", True),
        access_codes=reg_data.get("access_codes", []),
        allowed_email_domains=reg_data.get("allowed_email_domains", []),
        default_budget_usd=reg_data.get("default_budget_usd", 5.0),
    )
    
    # Parse server config
    srv_data = data.get("server", {})
    server = ServerConfig(
        public_api_url=srv_data.get("public_api_url", ""),
        default_model=srv_data.get("default_model", "default-model"),
        provider_timeout=srv_data.get("provider_timeout", 120.0),
        log_payload_max_bytes=srv_data.get("log_payload_max_bytes", 8192),
    )
    
    # Parse pricing config
    price_data = data.get("pricing", {})
    pricing = PricingConfig(
        default_input_per_million=price_data.get("default_input_per_million", 1.0),
        default_output_per_million=price_data.get("default_output_per_million", 3.0),
        fallback_min_charge_tokens=price_data.get("fallback_min_charge_tokens", 200),
        fallback_max_charge_tokens=price_data.get("fallback_max_charge_tokens", 4000),
    )
    
    settings = Settings(
        admin_password=data.get("admin_password", ""),
        registration=registration,
        server=server,
        pricing=pricing,
    )
    
    # Validate required settings
    if not settings.admin_password:
        print("\n" + "=" * 60)
        print("  ERROR: admin_password not set in config.json!")
        print("=" * 60 + "\n")
        sys.exit(1)
    
    return settings


# Load config once, expose both raw data and parsed settings
_raw_config = _load_config_file()
settings = _parse_settings(_raw_config)


def get_raw_config() -> dict:
    """Get the raw config data (for provider configuration)."""
    return _raw_config

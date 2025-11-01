"""Configuration management with environment validation."""
import os
import sys
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    provider_api_key: str = Field(default="")
    provider_base_url: str = Field(default="https://api.poe.com/v1")
    default_model: str = Field(default="GPT-5-nano")
    allowed_models: str = Field(default="GPT-5-nano,GPT-5-mini,Gemini-2.5-flash,Gemini-2.5-pro")
    database_url: str = Field(default="sqlite:///./data/tokenrouter.db")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    admin_password: str = Field(default="admin123")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def allowed_models_list(self) -> List[str]:
        """Parse allowed models from comma-separated string."""
        return [m.strip() for m in self.allowed_models.split(",") if m.strip()]
    
    def validate_api_key(self) -> None:
        """Prompt for API key if not provided."""
        if not self.provider_api_key:
            print("\n⚠️  Provider API key not found in environment!")
            print("Please enter your provider API key:")
            api_key = input("> ").strip()
            
            if not api_key:
                print("❌ API key is required. Exiting.")
                sys.exit(1)
            
            self.provider_api_key = api_key
            
            # Save to .env file for future use
            self._save_to_env_file(api_key)
    
    def _save_to_env_file(self, api_key: str) -> None:
        """Save API key to .env file."""
        try:
            env_path = ".env"
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    content = f.read()
                
                if "PROVIDER_API_KEY" in content:
                    # Update existing key
                    lines = content.split("\n")
                    new_lines = []
                    for line in lines:
                        if line.startswith("PROVIDER_API_KEY"):
                            new_lines.append(f"PROVIDER_API_KEY={api_key}")
                        else:
                            new_lines.append(line)
                    content = "\n".join(new_lines)
                else:
                    # Append new key
                    content += f"\nPROVIDER_API_KEY={api_key}\n"
                
                with open(env_path, "w") as f:
                    f.write(content)
            else:
                # Create new .env file
                with open(env_path, "w") as f:
                    f.write(f"PROVIDER_API_KEY={api_key}\n")
                    f.write(f"PROVIDER_BASE_URL={self.provider_base_url}\n")
                    f.write(f"DEFAULT_MODEL={self.default_model}\n")
                    f.write(f"ALLOWED_MODELS={self.allowed_models}\n")
            
            print(f"✅ API key saved to {env_path}")
        except Exception as e:
            print(f"⚠️  Could not save to .env file: {e}")


settings = Settings()


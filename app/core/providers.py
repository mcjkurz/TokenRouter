"""Provider configuration and model routing."""
import json
import fnmatch
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class Provider:
    """Represents an upstream LLM provider."""
    name: str
    base_url: str
    api_key: Optional[str]
    models: List[str]
    
    def matches_model(self, model: str) -> bool:
        """Check if this provider handles the given model using glob patterns."""
        model_lower = model.lower()
        for pattern in self.models:
            pattern_lower = pattern.lower()
            if fnmatch.fnmatch(model_lower, pattern_lower):
                return True
        return False


class ProviderConfig:
    """Manages provider configuration from JSON file."""
    
    def __init__(self, config_path: str = "providers.json"):
        self.config_path = Path(config_path)
        self.providers: Dict[str, Provider] = {}
        self.default_provider_name: Optional[str] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load provider configuration from JSON file."""
        if not self.config_path.exists():
            print("\n" + "="*60)
            print("  ERROR: providers.json not found!")
            print("="*60)
            print(f"\nExpected path: {self.config_path.absolute()}")
            print("\nTo configure providers:")
            print("\n1. Copy providers.example.json to providers.json:")
            print("   cp providers.example.json providers.json")
            print("\n2. Edit providers.json with your provider settings")
            print("="*60 + "\n")
            sys.exit(1)
        
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print("\n" + "="*60)
            print("  ERROR: Invalid JSON in providers.json!")
            print("="*60)
            print(f"\nParse error: {e}")
            print("\nPlease check your providers.json syntax.")
            print("="*60 + "\n")
            sys.exit(1)
        
        self.default_provider_name = data.get("default_provider")
        providers_data = data.get("providers", {})
        
        if not providers_data:
            print("\n" + "="*60)
            print("  ERROR: No providers defined in providers.json!")
            print("="*60)
            print("\nAt least one provider must be configured.")
            print("="*60 + "\n")
            sys.exit(1)
        
        for name, config in providers_data.items():
            self.providers[name] = Provider(
                name=name,
                base_url=config.get("base_url", ""),
                api_key=config.get("api_key"),
                models=config.get("models", [])
            )
        
        if self.default_provider_name and self.default_provider_name not in self.providers:
            print("\n" + "="*60)
            print("  ERROR: Default provider not found!")
            print("="*60)
            print(f"\nDefault provider '{self.default_provider_name}' is not defined in providers.")
            print(f"Available providers: {', '.join(self.providers.keys())}")
            print("="*60 + "\n")
            sys.exit(1)
    
    def get_provider_for_model(self, model: str) -> Optional[Provider]:
        """
        Find the provider that handles the given model.
        
        Checks all providers' model patterns, returns the first match.
        Falls back to default_provider if no specific match found.
        """
        for name, provider in self.providers.items():
            if name == self.default_provider_name:
                continue
            if provider.matches_model(model):
                return provider
        
        if self.default_provider_name:
            return self.providers.get(self.default_provider_name)
        
        return None
    
    def get_provider_by_name(self, name: str) -> Optional[Provider]:
        """Get a provider by its name."""
        return self.providers.get(name)
    
    @property
    def default_provider(self) -> Optional[Provider]:
        """Get the default provider."""
        if self.default_provider_name:
            return self.providers.get(self.default_provider_name)
        return None
    
    def get_all_models(self) -> List[str]:
        """
        Get all model patterns from all providers.
        
        Returns patterns with wildcards expanded to readable names where possible.
        """
        models = []
        for provider in self.providers.values():
            models.extend(provider.models)
        return models
    
    def get_all_model_names(self) -> List[str]:
        """
        Get unique model names/patterns for display.
        
        Removes duplicates and sorts alphabetically.
        """
        seen = set()
        models = []
        for provider in self.providers.values():
            for model in provider.models:
                if model.lower() not in seen:
                    seen.add(model.lower())
                    models.append(model)
        return sorted(models)
    
    def is_model_allowed(self, model: str) -> bool:
        """Check if any provider can handle this model."""
        return self.get_provider_for_model(model) is not None
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self.providers.clear()
        self.default_provider_name = None
        self._load_config()


provider_config = ProviderConfig()

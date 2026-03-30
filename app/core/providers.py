"""Provider configuration and model routing from providers.json."""
import json
import fnmatch
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


def _is_wildcard_pattern(pattern: str) -> bool:
    """Check if a pattern contains wildcard characters."""
    return any(c in pattern for c in "*?[")


@dataclass
class Provider:
    name: str
    base_url: str
    api_key: Optional[str]
    models: List[str]

    def matches_model_exact(self, model: str) -> bool:
        """Check for exact (non-wildcard) match."""
        model_lower = model.lower()
        return any(
            not _is_wildcard_pattern(p) and model_lower == p.lower()
            for p in self.models
        )

    def matches_model_wildcard(self, model: str) -> bool:
        """Check for wildcard match only."""
        model_lower = model.lower()
        return any(
            _is_wildcard_pattern(p) and fnmatch.fnmatch(model_lower, p.lower())
            for p in self.models
        )

    def matches_model(self, model: str) -> bool:
        """Check if model matches (exact or wildcard)."""
        return self.matches_model_exact(model) or self.matches_model_wildcard(model)


class ProviderConfig:
    def __init__(self, config_path: str = "providers.json"):
        self.config_path = Path(config_path)
        self.providers: Dict[str, Provider] = {}
        self.default_provider_name: Optional[str] = None
        self.default_model: Optional[str] = None
        self._load()

    def _load(self) -> None:
        if not self.config_path.exists():
            print(f"\n  ERROR: {self.config_path} not found!")
            print("  Run: cp providers.example.json providers.json\n")
            sys.exit(1)

        try:
            data = json.loads(self.config_path.read_text())
        except json.JSONDecodeError as e:
            print(f"\n  ERROR: Invalid JSON in {self.config_path}: {e}\n")
            sys.exit(1)

        self.default_provider_name = data.get("default_provider")
        self.default_model = data.get("default_model")
        for name, cfg in data.get("providers", {}).items():
            self.providers[name] = Provider(
                name=name,
                base_url=cfg.get("base_url", ""),
                api_key=cfg.get("api_key"),
                models=cfg.get("models", []),
            )

        _LOCAL_PREFIXES = ("http://localhost", "http://127.0.0.1")
        for name, provider in self.providers.items():
            is_local = any(provider.base_url.startswith(p) for p in _LOCAL_PREFIXES)
            if not is_local and not provider.base_url.startswith("https://"):
                print(f"\n  ERROR: Provider '{name}' base_url must start with https:// "
                      f"(got '{provider.base_url}')\n")
                sys.exit(1)

        if not self.providers:
            print("\n  ERROR: No providers defined in providers.json\n")
            sys.exit(1)

        if self.default_provider_name and self.default_provider_name not in self.providers:
            print(f"\n  ERROR: Default provider '{self.default_provider_name}' not found in providers\n")
            sys.exit(1)

    def get_provider_for_model(self, model: str) -> Optional[Provider]:
        """
        Return a provider that explicitly matches the model.
        
        Matching priority:
        1. Exact (non-wildcard) match — first provider found wins
        2. Wildcard match — non-default providers first, then default
        
        Returns None if no provider's pattern matches the model.
        """
        # Pass 1: exact matches have highest priority
        for p in self.providers.values():
            if p.matches_model_exact(model):
                return p

        # Pass 2: wildcard matches — prefer non-default providers
        candidates = [
            p for name, p in self.providers.items()
            if name != self.default_provider_name and p.matches_model_wildcard(model)
        ]
        if candidates:
            return random.choice(candidates)

        # Pass 3: check default provider for wildcard match
        if self.default_provider_name:
            default = self.providers.get(self.default_provider_name)
            if default and default.matches_model_wildcard(model):
                return default

        return None

    def is_model_allowed(self, model: str) -> bool:
        return self.get_provider_for_model(model) is not None

    def get_all_model_names(self) -> List[str]:
        seen = set()
        out = []
        for p in self.providers.values():
            for m in p.models:
                if m.lower() not in seen:
                    seen.add(m.lower())
                    out.append(m)
        return sorted(out)

    def get_all_models_with_providers(self) -> List[tuple]:
        """Return list of (model_name, provider_name) tuples, sorted by model name."""
        seen = set()
        out = []
        for p in self.providers.values():
            for m in p.models:
                if m.lower() not in seen:
                    seen.add(m.lower())
                    out.append((m, p.name))
        return sorted(out, key=lambda x: x[0].lower())

    def resolve_model(self, model: str) -> str:
        """Replace 'default' or 'default-model' with the configured default_model."""
        if model.lower() in ("default", "default-model") and self.default_model:
            return self.default_model
        return model

    def reload(self) -> None:
        self.providers.clear()
        self.default_provider_name = None
        self.default_model = None
        self._load()


provider_config = ProviderConfig()

"""
TSM Configuration Management
=============================

Centralized configuration system with:
- Environment-based configs (dev, staging, prod)
- Type validation
- Secret management
- Hot reloading
- Configuration versioning
"""

import os
import json
import yaml
from typing import Any, Dict, Optional, List, Type, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class ConfigSource(str, Enum):
    """Configuration sources."""

    FILE = "file"
    ENV = "env"
    DICT = "dict"
    SECRET_MANAGER = "secret_manager"


@dataclass
class SecretConfig:
    """Configuration for secret management."""

    provider: str = "env"  # env, file, aws_secrets_manager, etc.
    prefix: str = "TSM_"
    mask_in_logs: bool = True
    require_encryption: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5
    json_logs: bool = False


@dataclass
class DatabaseConfig:
    """Database configuration."""

    type: str = "sqlite"
    host: str = "localhost"
    port: int = 5432
    name: str = "tsm.db"
    user: str = ""
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False


@dataclass
class CacheConfig:
    """Cache configuration."""

    type: str = "memory"  # memory, redis
    host: str = "localhost"
    port: int = 6379
    ttl_seconds: int = 3600
    max_size: int = 10000
    enabled: bool = True


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    enabled: bool = True
    default_tier: str = "free"
    window_seconds: int = 3600
    burst_multiplier: float = 1.5


@dataclass
class ModelConfig:
    """Model configuration."""

    default_provider: str = "local"
    default_model: str = "llama3.2"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    enable_fallback: bool = True
    cost_threshold_usd: float = 0.01  # Alert if cost exceeds this per request


@dataclass
class SecurityConfig:
    """Security configuration."""

    enable_pii_detection: bool = True
    enable_sanitization: bool = True
    strict_mode: bool = True
    require_https: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    api_key_header: str = "X-API-Key"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24


@dataclass
class ObservabilityConfig:
    """Observability configuration."""

    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_analytics: bool = True
    tracing_sample_rate: float = 1.0
    metrics_export_interval_seconds: int = 60
    trace_exporter: str = "console"  # console, jaeger, zipkin


@dataclass
class ResilienceConfig:
    """Resilience configuration."""

    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    enable_retry: bool = True
    max_retries: int = 3
    retry_backoff_base: float = 1.0


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    log_level: str = "info"
    access_log: bool = True
    proxy_headers: bool = True
    forwarded_allow_ips: str = "*"


@dataclass
class TSMConfig:
    """
    Main TSM configuration.

    Aggregates all configuration sections.
    """

    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    version: str = "1.0.0"

    # Sub-configurations
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    resilience: ResilienceConfig = field(default_factory=ResilienceConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    secrets: SecretConfig = field(default_factory=SecretConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Environment-specific validation
        if self.environment == Environment.PRODUCTION:
            if self.debug:
                errors.append("Debug mode should be disabled in production")

            if self.security.jwt_secret == "":
                errors.append("JWT secret must be set in production")

            if not self.security.require_https:
                errors.append("HTTPS should be required in production")

            if self.server.reload:
                errors.append("Server auto-reload should be disabled in production")

        # Database validation
        if self.database.type == "postgres":
            if not self.database.user or not self.database.password:
                errors.append("Database user and password required for PostgreSQL")

        # Cache validation
        if self.cache.type == "redis":
            if not self.cache.host:
                errors.append("Redis host must be specified")

        # Model validation
        if self.model.timeout_seconds <= 0:
            errors.append("Model timeout must be positive")

        # Rate limit validation
        if self.rate_limit.enabled:
            if self.rate_limit.window_seconds <= 0:
                errors.append("Rate limit window must be positive")

        return errors

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEVELOPMENT


class ConfigLoader(ABC):
    """Base class for configuration loaders."""

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """Load configuration from source."""
        pass


class FileConfigLoader(ConfigLoader):
    """Load configuration from file (JSON or YAML)."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def load(self) -> Dict[str, Any]:
        """Load from file."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.file_path}")

        with open(self.file_path, "r") as f:
            if self.file_path.suffix in [".yaml", ".yml"]:
                return yaml.safe_load(f) or {}
            elif self.file_path.suffix == ".json":
                return json.load(f)
            else:
                raise ValueError(f"Unsupported config file type: {self.file_path.suffix}")


class EnvConfigLoader(ConfigLoader):
    """Load configuration from environment variables."""

    def __init__(self, prefix: str = "TSM_"):
        self.prefix = prefix

    def load(self) -> Dict[str, Any]:
        """Load from environment variables."""
        config = {}

        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(self.prefix):].lower()

                # Parse nested keys (e.g., TSM_DATABASE_HOST -> database.host)
                parts = config_key.split("_")
                current = config

                for i, part in enumerate(parts[:-1]):
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                # Set value (try to parse as JSON for complex types)
                try:
                    current[parts[-1]] = json.loads(value)
                except json.JSONDecodeError:
                    current[parts[-1]] = value

        return config


class DictConfigLoader(ConfigLoader):
    """Load configuration from dictionary."""

    def __init__(self, config_dict: Dict[str, Any]):
        self.config_dict = config_dict

    def load(self) -> Dict[str, Any]:
        """Load from dictionary."""
        return self.config_dict.copy()


class ConfigManager:
    """
    Configuration manager with hot reloading and validation.

    Usage:
        manager = ConfigManager()
        manager.load_from_file("config.yaml")
        manager.load_from_env()

        config = manager.get_config()

        # Access nested values
        db_host = config.database.host
        log_level = config.logging.level
    """

    def __init__(self):
        self._config: Optional[TSMConfig] = None
        self._loaders: List[ConfigLoader] = []
        self._watch_files: List[Path] = []

    def load_from_file(self, file_path: str) -> "ConfigManager":
        """Load configuration from file."""
        loader = FileConfigLoader(file_path)
        self._loaders.append(loader)
        self._watch_files.append(Path(file_path))
        return self

    def load_from_env(self, prefix: str = "TSM_") -> "ConfigManager":
        """Load configuration from environment variables."""
        loader = EnvConfigLoader(prefix)
        self._loaders.append(loader)
        return self

    def load_from_dict(self, config_dict: Dict[str, Any]) -> "ConfigManager":
        """Load configuration from dictionary."""
        loader = DictConfigLoader(config_dict)
        self._loaders.append(loader)
        return self

    def build(self) -> TSMConfig:
        """
        Build final configuration by merging all sources.

        Priority (highest to lowest):
        1. Environment variables
        2. Config files (in order added)
        3. Defaults
        """
        merged = {}

        # Load and merge all sources
        for loader in self._loaders:
            config_data = loader.load()
            merged = self._deep_merge(merged, config_data)

        # Convert to TSMConfig
        self._config = self._dict_to_config(merged)

        # Validate
        errors = self._config.validate()
        if errors:
            logger.warning(f"Configuration validation warnings: {errors}")

        logger.info(f"Configuration loaded: environment={self._config.environment.value}")

        return self._config

    def get_config(self) -> TSMConfig:
        """Get current configuration."""
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call build() first.")
        return self._config

    def reload(self) -> TSMConfig:
        """Reload configuration from sources."""
        logger.info("Reloading configuration...")
        return self.build()

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _dict_to_config(self, data: Dict[str, Any]) -> TSMConfig:
        """Convert dictionary to TSMConfig."""
        # Extract environment
        env_str = data.get("environment", "development")
        environment = Environment(env_str) if isinstance(env_str, str) else env_str

        # Build sub-configs
        config = TSMConfig(
            environment=environment,
            debug=data.get("debug", environment == Environment.DEVELOPMENT),
            version=data.get("version", "1.0.0"),
        )

        # Load sub-configurations
        if "logging" in data:
            config.logging = LoggingConfig(**self._filter_valid_keys(data["logging"], LoggingConfig))

        if "database" in data:
            config.database = DatabaseConfig(**self._filter_valid_keys(data["database"], DatabaseConfig))

        if "cache" in data:
            config.cache = CacheConfig(**self._filter_valid_keys(data["cache"], CacheConfig))

        if "rate_limit" in data:
            config.rate_limit = RateLimitConfig(**self._filter_valid_keys(data["rate_limit"], RateLimitConfig))

        if "model" in data:
            config.model = ModelConfig(**self._filter_valid_keys(data["model"], ModelConfig))

        if "security" in data:
            config.security = SecurityConfig(**self._filter_valid_keys(data["security"], SecurityConfig))

        if "observability" in data:
            config.observability = ObservabilityConfig(**self._filter_valid_keys(data["observability"], ObservabilityConfig))

        if "resilience" in data:
            config.resilience = ResilienceConfig(**self._filter_valid_keys(data["resilience"], ResilienceConfig))

        if "server" in data:
            config.server = ServerConfig(**self._filter_valid_keys(data["server"], ServerConfig))

        if "secrets" in data:
            config.secrets = SecretConfig(**self._filter_valid_keys(data["secrets"], SecretConfig))

        return config

    def _filter_valid_keys(self, data: Dict[str, Any], dataclass_type: Type) -> Dict[str, Any]:
        """Filter dictionary to only include valid dataclass fields."""
        valid_keys = {f.name for f in dataclass_type.__dataclass_fields__.values()}
        return {k: v for k, v in data.items() if k in valid_keys}


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> TSMConfig:
    """
    Get global configuration instance.

    Lazy loads from default sources if not already loaded.
    """
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigManager()

        # Try to load from file
        config_file = os.getenv("TSM_CONFIG_FILE", "config.yaml")
        if os.path.exists(config_file):
            _config_manager.load_from_file(config_file)

        # Always load from environment (overrides file)
        _config_manager.load_from_env()

        # Build final config
        _config_manager.build()

    return _config_manager.get_config()


def init_config(
    config_file: Optional[str] = None,
    config_dict: Optional[Dict[str, Any]] = None,
    load_env: bool = True,
) -> TSMConfig:
    """
    Initialize global configuration.

    Args:
        config_file: Path to config file (YAML or JSON)
        config_dict: Configuration dictionary
        load_env: Load from environment variables

    Returns:
        TSMConfig instance
    """
    global _config_manager

    _config_manager = ConfigManager()

    if config_file:
        _config_manager.load_from_file(config_file)

    if config_dict:
        _config_manager.load_from_dict(config_dict)

    if load_env:
        _config_manager.load_from_env()

    return _config_manager.build()


def reload_config() -> TSMConfig:
    """Reload configuration from sources."""
    global _config_manager

    if _config_manager is None:
        raise RuntimeError("Configuration not initialized")

    return _config_manager.reload()


__all__ = [
    "TSMConfig",
    "Environment",
    "ConfigSource",
    "LoggingConfig",
    "DatabaseConfig",
    "CacheConfig",
    "RateLimitConfig",
    "ModelConfig",
    "SecurityConfig",
    "ObservabilityConfig",
    "ResilienceConfig",
    "ServerConfig",
    "SecretConfig",
    "ConfigManager",
    "get_config",
    "init_config",
    "reload_config",
]

"""
Configuration Loader Utility

This module provides a centralized way to load and access configuration
from YAML files with environment variable overrides.

Usage:
    from common.config_loader import load_config

    config = load_config()
    kafka_broker = config.get('kafka.broker')
    postgres_host = config.get('postgres.host')
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Configuration loader with nested key access and environment variable override."""

    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., 'kafka.broker')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get('kafka.broker')
            'kafka:9092'
            >>> config.get('kafka.producer.batch_size')
            16384
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        # Handle environment variable substitution
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.getenv(env_var, default)

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section: Section name (e.g., 'kafka', 'postgres')

        Returns:
            Dictionary containing the section
        """
        return self.get(section, {})

    def to_dict(self) -> Dict[str, Any]:
        """Return the entire configuration as a dictionary."""
        return self._config.copy()


def substitute_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively substitute environment variables in config values.

    Supports syntax: ${ENV_VAR_NAME} or ${ENV_VAR_NAME:default_value}

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with substituted values
    """
    if isinstance(config, dict):
        return {k: substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [substitute_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Handle ${VAR} syntax
        if config.startswith('${') and config.endswith('}'):
            var_spec = config[2:-1]
            # Support default values: ${VAR:default}
            if ':' in var_spec:
                var_name, default = var_spec.split(':', 1)
                return os.getenv(var_name, default)
            else:
                return os.getenv(var_spec, config)
        return config
    else:
        return config


def load_config(config_path: Optional[str] = None, env: Optional[str] = None) -> ConfigLoader:
    """
    Load configuration from YAML file with environment variable overrides.

    Args:
        config_path: Path to configuration file. If None, looks for:
                    1. CONFIG_PATH environment variable
                    2. config/conf.yaml (default)
        env: Environment name (e.g., 'dev', 'prod'). If specified, loads
             config/conf.{env}.yaml in addition to base config.
             Can also be set via ENVIRONMENT variable.

    Returns:
        ConfigLoader instance

    Example:
        >>> config = load_config()
        >>> config = load_config('config/conf.prod.yaml')
        >>> config = load_config(env='prod')  # Loads conf.yaml + conf.prod.yaml
    """
    # Determine config file path
    if config_path is None:
        config_path = os.getenv('CONFIG_PATH')

    if config_path is None:
        # Default to config/conf.yaml relative to project root
        project_root = Path(__file__).parent.parent
        config_path = project_root / 'config' / 'conf.yaml'

    config_path = Path(config_path)

    # Check if file exists
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}. Using defaults.")
        return ConfigLoader({})

    # Load base configuration
    logger.info(f"Loading configuration from: {config_path}")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

    # Load environment-specific overrides
    if env is None:
        env = os.getenv('ENVIRONMENT')

    if env:
        env_config_path = config_path.parent / f'conf.{env}.yaml'
        if env_config_path.exists():
            logger.info(f"Loading environment config: {env_config_path}")
            with open(env_config_path, 'r') as f:
                env_config = yaml.safe_load(f) or {}
            # Deep merge environment config into base config
            config = deep_merge(config, env_config)
        else:
            logger.debug(f"No environment-specific config found: {env_config_path}")

    # Substitute environment variables
    config = substitute_env_vars(config)

    # Apply direct environment variable overrides
    config = apply_env_overrides(config)

    return ConfigLoader(config)


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary
        override: Dictionary with override values

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply direct environment variable overrides to configuration.

    Supports overriding nested keys using underscores:
    KAFKA_BROKER overrides kafka.broker
    POSTGRES_HOST overrides postgres.host

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with overrides applied
    """
    # Common overrides
    overrides = {
        'KAFKA_BROKER': 'kafka.broker',
        'KAFKA_BOOTSTRAP_SERVERS': 'spark.kafka.bootstrap_servers',
        'POSTGRES_HOST': 'postgres.host',
        'POSTGRES_PORT': 'postgres.port',
        'POSTGRES_DB': 'postgres.database',
        'POSTGRES_USER': 'postgres.user',
        'POSTGRES_PASSWORD': 'postgres.password',
        'POSTGRES_JDBC_URL': 'postgres.jdbc_url',
        'SPARK_LOG_LEVEL': 'spark.log_level',
        'CHECKPOINT_LOCATION': 'spark.checkpoint.location',
    }

    for env_var, config_key in overrides.items():
        value = os.getenv(env_var)
        if value is not None:
            # Set nested config value
            keys = config_key.split('.')
            current = config
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
            logger.debug(f"Override {config_key} from {env_var}: {value}")

    return config


def validate_config(config: ConfigLoader) -> bool:
    """
    Validate required configuration values.

    Args:
        config: Configuration loader instance

    Returns:
        True if valid, raises ValueError if invalid
    """
    required_keys = [
        'kafka.broker',
        'kafka.topics.wiki_changes',
        'postgres.host',
        'postgres.database',
        'postgres.user',
    ]

    missing = []
    for key in required_keys:
        if config.get(key) is None:
            missing.append(key)

    if missing:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing)}")

    return True


# Convenience function for quick access
def get_config() -> ConfigLoader:
    """
    Get configuration with caching.

    Returns:
        Cached ConfigLoader instance
    """
    if not hasattr(get_config, '_cache'):
        get_config._cache = load_config()
    return get_config._cache

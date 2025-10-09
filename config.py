"""Configuration loader for multi-agent system"""

import os
import yaml
from typing import Dict, Any
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file with environment variable substitution"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Recursively substitute environment variables
    return _substitute_env_vars(config)


def _substitute_env_vars(obj: Any) -> Any:
    """Recursively substitute environment variables in config values"""
    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # Handle ${VAR} and ${VAR:default} syntax
        if obj.startswith("${") and obj.endswith("}"):
            var_expr = obj[2:-1]
            if ":" in var_expr:
                var_name, default = var_expr.split(":", 1)
                return os.environ.get(var_name, default)
            else:
                return os.environ.get(var_expr, "")
        return obj
    else:
        return obj


def get_agent_config(agent_name: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get configuration for a specific agent"""
    if config is None:
        config = load_config()

    agent_config = config.get("agents", {}).get(agent_name, {})
    api_provider = agent_config.get("api_provider", "openai")

    # Get API credentials based on provider
    api_config = config.get(api_provider, {})

    return {
        "model": agent_config.get("model"),
        "api_key": api_config.get("api_key"),
        "base_url": api_config.get("base_url"),
        "temperature": agent_config.get("temperature", 0.5),
        "max_tokens": agent_config.get("max_tokens", 1000),
        "api_provider": api_provider
    }


def get_tavily_api_key(config: Dict[str, Any] = None) -> str:
    """Get Tavily API key from config"""
    if config is None:
        config = load_config()
    return config.get("tavily", {}).get("api_key", "")

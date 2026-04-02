from __future__ import annotations

import os
from pathlib import Path
import tomllib

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
STREAMLIT_SECRETS_PATHS = [
    PROJECT_ROOT / ".streamlit" / "secrets.toml",
    Path.home() / ".streamlit" / "secrets.toml",
]


def load_yaml(relative_path: str) -> dict:
    with (CONFIG_DIR / relative_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_settings() -> dict:
    return load_yaml("settings.yaml")


def load_assets_config() -> list[dict]:
    return load_yaml("assets.yaml").get("assets", [])


def load_proxy_rules() -> list[dict]:
    return load_yaml("proxies.yaml").get("proxies", [])


def load_local_secrets() -> dict:
    for path in STREAMLIT_SECRETS_PATHS:
        if not path.exists():
            continue
        with path.open("rb") as handle:
            return tomllib.load(handle)
    return {}


def get_secret(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    secrets = load_local_secrets()
    secret_value = secrets.get(name, default)
    if secret_value is None:
        return default
    return str(secret_value)

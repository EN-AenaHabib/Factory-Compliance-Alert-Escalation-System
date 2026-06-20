"""
src/common/config.py
Single shared config loader. Every module calls load_config() instead of
parsing config/config.yaml itself, so paths/thresholds stay in one place.
"""
import os
from pathlib import Path
from functools import lru_cache
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "config.yaml"


@lru_cache(maxsize=1)
def load_config(config_path: str | None = None) -> dict:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg


def resolve_path(relative_path: str) -> Path:
    """Resolve a path from config.yaml (always given relative to repo root)
    into an absolute Path, creating parent dirs if missing."""
    p = (REPO_ROOT / relative_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)

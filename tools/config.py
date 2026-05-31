from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

try:
    from .common import REPO_ROOT
except ImportError:
    from common import REPO_ROOT


DEFAULT_MINERU_ENDPOINT = "http://localhost:8000"
DEFAULT_MINERU_CLOUD_URL = "https://mineru.net/api/v4"


@dataclass
class MineruConfig:
    endpoint: str = DEFAULT_MINERU_ENDPOINT
    cloud_url: str = DEFAULT_MINERU_CLOUD_URL
    api_key: str = ""
    force_cloud: bool = False


def _read_local_config() -> dict:
    for path in (Path.cwd() / "config.local.yaml", REPO_ROOT / "config.local.yaml"):
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return data if isinstance(data, dict) else {}
    return {}


def resolve_mineru_config(args=None) -> MineruConfig:
    local = _read_local_config().get("mineru", {}) or {}
    return MineruConfig(
        endpoint=(
            getattr(args, "mineru_endpoint", None)
            or os.environ.get("MINERU_ENDPOINT")
            or local.get("endpoint")
            or DEFAULT_MINERU_ENDPOINT
        ),
        cloud_url=(
            getattr(args, "mineru_cloud_url", None)
            or os.environ.get("MINERU_CLOUD_URL")
            or local.get("cloud_url")
            or DEFAULT_MINERU_CLOUD_URL
        ),
        api_key=(
            getattr(args, "mineru_api_key", None)
            or os.environ.get("MINERU_API_KEY")
            or local.get("api_key")
            or ""
        ),
        force_cloud=bool(getattr(args, "force_cloud", False)),
    )

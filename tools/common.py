from __future__ import annotations

import re
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKDIR = REPO_ROOT / "work"


def slugify(text: str, *, fallback: str = "paper") -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return slug[:80] or fallback


def copytree_merge(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            copytree_merge(item, target)
        else:
            shutil.copy2(item, target)


def project_path(path: str | Path) -> Path:
    p = Path(path).expanduser()
    return p if p.is_absolute() else (Path.cwd() / p).resolve()

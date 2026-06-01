from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    from .common import DEFAULT_WORKDIR, copytree_merge, project_path, slugify
    from .config import MineruConfig
    from .mineru import convert_pdf
except ImportError:
    from common import DEFAULT_WORKDIR, copytree_merge, project_path, slugify
    from config import MineruConfig
    from mineru import convert_pdf


ARXIV_RE = re.compile(r"(?:arxiv:)?(\d{4}\.\d{4,5})(?:v\d+)?", re.I)


def ingest(input_value: str | Path, workdir: str | Path | None, mineru_cfg: MineruConfig | None = None) -> Path:
    mineru_cfg = mineru_cfg or MineruConfig()
    input_value = str(input_value)
    src = Path(input_value).expanduser()
    base_work = project_path(workdir) if workdir else DEFAULT_WORKDIR
    if src.exists():
        return _ingest_local(src, base_work, mineru_cfg)
    if _looks_like_arxiv(input_value):
        pdf = _download_arxiv(input_value, base_work)
        return _ingest_local(pdf, base_work, mineru_cfg)
    if input_value.startswith(("http://", "https://")):
        pdf = _download_pdf_url(input_value, base_work)
        return _ingest_local(pdf, base_work, mineru_cfg)
    raise ValueError(f"Unsupported input: {input_value}")


def _ingest_local(src: Path, base_work: Path, mineru_cfg: MineruConfig) -> Path:
    if src.is_dir() and (src / "paper.md").exists():
        paper_dir = base_work / slugify(src.name)
        paper_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / "paper.md", paper_dir / "paper.md")
        copytree_merge(src / "images", paper_dir / "images")
        _write_source(paper_dir, {"kind": "mineru_dir", "source": str(src)})
        return paper_dir
    if src.suffix.lower() == ".md":
        paper_dir = base_work / slugify(src.stem)
        paper_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, paper_dir / "paper.md")
        copytree_merge(src.parent / "images", paper_dir / "images")
        _write_source(paper_dir, {"kind": "markdown", "source": str(src)})
        return paper_dir
    if src.suffix.lower() == ".pdf":
        paper_dir = base_work / slugify(src.stem)
        paper_dir.mkdir(parents=True, exist_ok=True)
        dest_pdf = paper_dir / src.name
        if src.resolve() != dest_pdf.resolve():
            shutil.copy2(src, dest_pdf)
        convert_pdf(dest_pdf, paper_dir, mineru_cfg)
        _write_source(paper_dir, {"kind": "pdf", "source": str(src)})
        return paper_dir
    raise ValueError(f"Unsupported local input: {src}")


def _looks_like_arxiv(value: str) -> bool:
    return bool(ARXIV_RE.search(value)) or "arxiv.org" in value


def _download_arxiv(value: str, base_work: Path) -> Path:
    match = ARXIV_RE.search(value)
    if not match:
        raise ValueError(f"Could not parse arXiv id: {value}")
    arxiv_id = match.group(1)
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    dest_dir = base_work / slugify(f"arxiv-{arxiv_id}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"arxiv-{arxiv_id}.pdf"
    _download(url, dest)
    return dest


def _download_pdf_url(url: str, base_work: Path) -> Path:
    parsed = urlparse(url)
    name = Path(parsed.path).name or "paper.pdf"
    if not name.lower().endswith(".pdf"):
        raise ValueError("URL does not look like a direct PDF URL")
    dest_dir = base_work / slugify(Path(name).stem)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    _download(url, dest)
    return dest


def _download(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def _write_source(paper_dir: Path, payload: dict) -> None:
    (paper_dir / "source.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

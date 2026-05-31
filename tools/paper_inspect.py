from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PIL import Image


IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)")
HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$", re.MULTILINE)


def _image_size(path: Path) -> tuple[int, int]:
    if path.suffix.lower() == ".svg":
        text = path.read_text(encoding="utf-8", errors="ignore")
        width = re.search(r'\bwidth=["\']?([0-9.]+)', text)
        height = re.search(r'\bheight=["\']?([0-9.]+)', text)
        if width and height:
            return int(float(width.group(1))), int(float(height.group(1)))
        viewbox = re.search(r'\bviewBox=["\']([0-9.\s-]+)["\']', text)
        if viewbox:
            parts = [float(x) for x in viewbox.group(1).split()]
            if len(parts) == 4:
                return int(parts[2]), int(parts[3])
        return 0, 0

    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return 0, 0


def inspect_paper(paper_dir: str | Path, output: str | Path | None = None) -> dict[str, Any]:
    paper_dir = Path(paper_dir).expanduser().resolve()
    md_path = paper_dir / "paper.md"
    if not md_path.exists():
        raise FileNotFoundError(f"缺少 paper.md: {md_path}")

    md = md_path.read_text(encoding="utf-8", errors="ignore")
    headings = [
        {"level": len(match.group("marks")), "title": match.group("title").strip()}
        for match in HEADING_RE.finditer(md)
    ]

    referenced_images: list[dict[str, Any]] = []
    for idx, match in enumerate(IMAGE_RE.finditer(md), start=1):
        rel = match.group("path").strip()
        img_path = (paper_dir / rel).resolve()
        width, height = _image_size(img_path) if img_path.exists() else (0, 0)
        referenced_images.append(
            {
                "index": idx,
                "alt": match.group("alt").strip(),
                "path": rel,
                "exists": img_path.exists(),
                "width": width,
                "height": height,
            }
        )

    image_dir = paper_dir / "images"
    image_files = []
    if image_dir.exists():
        for path in sorted(image_dir.iterdir()):
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
                width, height = _image_size(path)
                image_files.append(
                    {
                        "path": str(path.relative_to(paper_dir)),
                        "width": width,
                        "height": height,
                        "referenced": any(item["path"] == str(path.relative_to(paper_dir)) for item in referenced_images),
                    }
                )

    result = {
        "paper_dir": str(paper_dir),
        "markdown": str(md_path),
        "title": headings[0]["title"] if headings else paper_dir.name,
        "word_count": len(re.findall(r"\w+", md)),
        "headings": headings,
        "referenced_images": referenced_images,
        "figures": referenced_images,
        "image_files": image_files,
        "notes": [
            "This is deterministic inventory only; the agent/LLM should still decide the scientific story and figure priority."
        ],
    }

    if output:
        output = Path(output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result

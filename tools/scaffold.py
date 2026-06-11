from __future__ import annotations

import html
import shutil
from pathlib import Path

try:
    from .common import REPO_ROOT, project_path
    from .paper_inspect import inspect_paper
except ImportError:
    from common import REPO_ROOT, project_path
    from paper_inspect import inspect_paper


DEFAULT_FORMAT = "screen"
DEFAULT_TEMPLATE = REPO_ROOT / "templates" / "screen_16x9_figure_focus.html"
FORMAT_TEMPLATES = {
    "screen": DEFAULT_TEMPLATE,
    "phone": REPO_ROOT / "templates" / "phone_9x16_figure_focus.html",
}


def scaffold(
    paper_dir: str | Path,
    template: str | Path | None = None,
    *,
    overwrite: bool = False,
    figure_count: int = 4,
    format: str = DEFAULT_FORMAT,
) -> Path:
    paper_dir = project_path(paper_dir)
    if figure_count not in (1, 2, 3, 4):
        raise ValueError("figure_count must be between 1 and 4")
    if format not in FORMAT_TEMPLATES:
        raise ValueError(f"format must be one of: {', '.join(FORMAT_TEMPLATES)}")
    poster_path = paper_dir / "poster.html"
    if poster_path.exists() and not overwrite:
        return poster_path
    template_path = project_path(template) if template else FORMAT_TEMPLATES[format]
    content = template_path.read_text(encoding="utf-8")
    info = inspect_paper(paper_dir)
    figures = info.get("referenced_images", info.get("figures", []))[:figure_count]
    figure_html = "\n".join(_figure_card(fig, i + 1) for i, fig in enumerate(figures)) or _figure_placeholder()
    figure_panel_attrs = _figure_panel_attrs(len(figures))
    defaults = _copy_defaults(format)
    content = (
        content.replace("{{HEADLINE}}", defaults["headline"])
        .replace("{{SUBTITLE}}", defaults["subtitle"])
        .replace("{{PAPER_TITLE}}", html.escape(info.get("title") or paper_dir.name))
        .replace("{{PAPER_META}}", "First author / year / source")
        .replace("{{BACKGROUND}}", defaults["background"])
        .replace("{{KNOWLEDGE_GAP}}", defaults["knowledge_gap"])
        .replace("{{SELLING}}", defaults["selling"])
        .replace("{{KEY_RESULTS}}", defaults["key_results"])
        .replace("{{FIGURE_PANEL_ATTRS}}", figure_panel_attrs)
        .replace("{{FIGURES}}", figure_html)
    )
    poster_path.write_text(content, encoding="utf-8")
    assets = paper_dir / "assets"
    if (paper_dir / "images").exists() and not assets.exists():
        shutil.copytree(paper_dir / "images", assets)
    return poster_path


def _figure_card(fig: dict, idx: int) -> str:
    src = html.escape(fig.get("path", "").replace("images/", "assets/"))
    fig_no = fig.get("index", idx)
    caption = html.escape(fig.get("alt") or f"TODO: explain why Figure {fig_no} matters")
    return f'''<figure class="figure-card" data-role="figure-card">
  <img src="{src}" alt="Figure {fig_no}">
  <figcaption><strong>Fig. {fig_no}.</strong> {caption}</figcaption>
</figure>'''


def _figure_panel_attrs(figure_count: int) -> str:
    layout_by_count = {
        1: "solo",
        2: "hero-1",
        3: "hero-2",
    }
    layout = layout_by_count.get(figure_count)
    return f' data-layout="{layout}"' if layout else ""


def _copy_defaults(format: str) -> dict[str, str]:
    if format == "phone":
        return {
            "headline": "What to remember",
            "subtitle": "A phone-sized pitch for the paper's strongest visual claim.",
            "background": "TODO: one-sentence reason this result matters.",
            "knowledge_gap": "Missing piece: what was uncertain before this paper?",
            "selling": "TODO: the paper's core claim in one or two short sentences.",
            "key_results": "<li>TODO: memorable evidence</li>",
        }
    return {
        "headline": "What we learn from this paper",
        "subtitle": "A compact, figure-first reading of the core evidence and why it matters.",
        "background": "TODO: Why should a broad astro audience care?",
        "knowledge_gap": "Knowledge gap: what is still missing before this problem is convincingly solved?",
        "selling": "TODO: What knowledge increment is this paper selling?",
        "key_results": "<li>TODO: observational fact supporting the main claim</li>",
    }


def _figure_placeholder() -> str:
    return '''<figure class="figure-card placeholder" data-role="figure-card">
  <div class="empty-figure">No figure selected yet</div>
  <figcaption>Run inspect, choose 2-4 figures, and replace this placeholder.</figcaption>
</figure>'''

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


DEFAULT_TEMPLATE = REPO_ROOT / "templates" / "screen_16x9_figure_focus.html"


def scaffold(paper_dir: str | Path, template: str | Path | None = None, *, overwrite: bool = False, figure_count: int = 4) -> Path:
    paper_dir = project_path(paper_dir)
    if figure_count not in (3, 4):
        raise ValueError("figure_count must be 3 or 4")
    poster_path = paper_dir / "poster.html"
    if poster_path.exists() and not overwrite:
        return poster_path
    template_path = project_path(template) if template else DEFAULT_TEMPLATE
    content = template_path.read_text(encoding="utf-8")
    info = inspect_paper(paper_dir)
    figures = info.get("referenced_images", info.get("figures", []))[:figure_count]
    figure_html = "\n".join(_figure_card(fig, i + 1) for i, fig in enumerate(figures)) or _figure_placeholder()
    figure_panel_attrs = ' data-layout="hero-2"' if len(figures) == 3 else ""
    content = (
        content.replace("{{HEADLINE}}", "What we learn from this paper")
        .replace("{{SUBTITLE}}", "A compact, figure-first reading of the core evidence and why it matters.")
        .replace("{{PAPER_TITLE}}", html.escape(info.get("title") or paper_dir.name))
        .replace("{{PAPER_META}}", "First author / year / source")
        .replace("{{BACKGROUND}}", "TODO: Why should a broad astro audience care?")
        .replace("{{KNOWLEDGE_GAP}}", "Knowledge gap: what is still missing before this problem is convincingly solved?")
        .replace("{{SELLING}}", "TODO: What knowledge increment is this paper selling?")
        .replace("{{KEY_RESULTS}}", "<li>TODO: observational fact supporting the main claim</li>")
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


def _figure_placeholder() -> str:
    return '''<figure class="figure-card placeholder" data-role="figure-card">
  <div class="empty-figure">No figure selected yet</div>
  <figcaption>Run inspect, choose 2-4 figures, and replace this placeholder.</figcaption>
</figure>'''

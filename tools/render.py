from __future__ import annotations

from pathlib import Path

try:
    from .check import check_html
    from .common import project_path
except ImportError:
    from check import check_html
    from common import project_path


def _wait_for_math(page) -> None:
    page.evaluate(
        """() => {
          if (!window.MathJax || !window.MathJax.startup || !window.MathJax.startup.promise) {
            return true;
          }
          return window.MathJax.startup.promise.then(() => true);
        }"""
    )


def render(
    html_path: str | Path,
    *,
    png: bool = True,
    pdf: bool = False,
    viewport: tuple[int, int] = (1920, 1080),
    force: bool = False,
) -> dict:
    html_path = project_path(html_path)
    layout_path = html_path.with_name("layout.json")
    if not force:
        result = check_html(html_path, json_out=layout_path, viewport=viewport)
        if result["errors"]:
            raise RuntimeError(f"layout check failed; see {layout_path}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright not installed; run `python -m playwright install chromium` after installing deps") from exc
    out: dict[str, str] = {}
    if layout_path.exists():
        out["layout"] = str(layout_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        page.goto(html_path.as_uri(), wait_until="networkidle")
        _wait_for_math(page)
        if png:
            png_path = html_path.with_name("poster_preview.png")
            page.screenshot(path=str(png_path), full_page=False)
            out["png"] = str(png_path)
        if pdf:
            pdf_path = html_path.with_name("poster.pdf")
            page.pdf(path=str(pdf_path), width=f"{viewport[0]}px", height=f"{viewport[1]}px", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            out["pdf"] = str(pdf_path)
        browser.close()
    return out

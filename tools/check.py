from __future__ import annotations

import json
from pathlib import Path

from bs4 import BeautifulSoup

try:
    from .common import project_path
except ImportError:
    from common import project_path


REQUIRED_ROLES = ["poster", "header", "headline", "meta", "text-column", "figure-panel", "figure-card"]


def _wait_for_math(page) -> None:
    page.evaluate(
        """() => {
          if (!window.MathJax || !window.MathJax.startup || !window.MathJax.startup.promise) {
            return true;
          }
          return window.MathJax.startup.promise.then(() => true);
        }"""
    )


def check_html(
    html_path: str | Path,
    *,
    json_out: str | Path | None = None,
    viewport: tuple[int, int] = (1920, 1080),
    dynamic: bool = True,
) -> dict:
    html_path = project_path(html_path)
    static = _static_checks(html_path)
    dynamic_result = _playwright_checks(html_path, viewport) if dynamic else {"errors": [], "warnings": [], "measurements": {}}
    result = {
        "html": str(html_path),
        "viewport": {"width": viewport[0], "height": viewport[1]},
        "errors": static["errors"] + dynamic_result["errors"],
        "warnings": static["warnings"] + dynamic_result["warnings"],
        "measurements": dynamic_result["measurements"],
    }
    result["ok"] = not result["errors"]
    if json_out:
        project_path(json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def _static_checks(html_path: Path) -> dict:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    errors: list[str] = []
    warnings: list[str] = []
    for role in REQUIRED_ROLES:
        if not soup.select(f'[data-role="{role}"]'):
            errors.append(f'missing data-role="{role}"')
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src.startswith(("http://", "https://", "data:")):
            continue
        if src and not (html_path.parent / src).exists():
            errors.append(f"broken image: {src}")
    return {"errors": errors, "warnings": warnings}


def _playwright_checks(html_path: Path, viewport: tuple[int, int]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    measurements: dict = {}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        warnings.append("playwright not installed; dynamic layout checks skipped")
        return {"errors": errors, "warnings": warnings, "measurements": measurements}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        page.goto(html_path.as_uri(), wait_until="networkidle")
        _wait_for_math(page)
        data = page.evaluate(
            """() => {
              const box = sel => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return {x:r.x,y:r.y,w:r.width,h:r.height,bottom:r.bottom,right:r.right,scrollH:el.scrollHeight,clientH:el.clientHeight};
              };
              const figs = Array.from(document.querySelectorAll('[data-role="figure-card"]')).map(card => {
                const r = card.getBoundingClientRect();
                const img = card.querySelector('img');
                const ir = img ? img.getBoundingClientRect() : null;
                return {card:{w:r.width,h:r.height}, img: ir ? {w:ir.width,h:ir.height} : null};
              });
              const textCards = Array.from(document.querySelectorAll('.text-card')).map(card => {
                const r = card.getBoundingClientRect();
                return {w:r.width,h:r.height,scrollH:card.scrollHeight,clientH:card.clientHeight};
              });
              const captions = Array.from(document.querySelectorAll('[data-role="figure-card"] figcaption')).map(cap => {
                const r = cap.getBoundingClientRect();
                return {w:r.width,h:r.height,scrollH:cap.scrollHeight,clientH:cap.clientHeight};
              });
              return {
                bodyScrollW: document.documentElement.scrollWidth,
                bodyScrollH: document.documentElement.scrollHeight,
                viewportW: window.innerWidth,
                viewportH: window.innerHeight,
                poster: box('[data-role="poster"]'),
                header: box('[data-role="header"]'),
                text: box('[data-role="text-column"]'),
                figurePanel: box('[data-role="figure-panel"]'),
                figures: figs,
                textCards,
                captions
              };
            }"""
        )
        browser.close()
    measurements = data
    if data["bodyScrollW"] > viewport[0] + 2 or data["bodyScrollH"] > viewport[1] + 2:
        errors.append("page scrolls beyond viewport")
    header = data.get("header") or {}
    if header.get("h", 0) > viewport[1] * 0.2:
        errors.append("header exceeds 20% of viewport height")
    text = data.get("text") or {}
    if text and text.get("scrollH", 0) > text.get("clientH", 0) + 2:
        errors.append("text column overflows")
    for i, card in enumerate(data.get("textCards") or [], 1):
        if card.get("scrollH", 0) > card.get("clientH", 0) + 2:
            errors.append(f"text card {i} overflows")
    for i, caption in enumerate(data.get("captions") or [], 1):
        if caption.get("scrollH", 0) > caption.get("clientH", 0) + 2:
            errors.append(f"figure caption {i} overflows")
    for i, fig in enumerate(data.get("figures") or [], 1):
        img = fig.get("img")
        if not img:
            errors.append(f"figure card {i} has no image")
            continue
        if img["w"] < 360 or img["h"] < 220:
            warnings.append(f"figure card {i} image may be too small ({img['w']:.0f}x{img['h']:.0f}px)")
    return {"errors": errors, "warnings": warnings, "measurements": measurements}

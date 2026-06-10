from __future__ import annotations

import json
from pathlib import Path

from bs4 import BeautifulSoup

try:
    from .common import project_path
except ImportError:
    from common import project_path


REQUIRED_ROLES = ["poster", "header", "headline", "meta", "text-column", "figure-panel", "figure-card"]
CANVAS_TOLERANCE_PX = 2
OVERFLOW_TOLERANCE_PX = 6
MIN_TEXT_CARD_HEIGHT_PX = 32


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
    dynamic_result = (
        _playwright_checks(html_path, viewport)
        if dynamic
        else {"errors": [], "warnings": [], "error_details": [], "warning_details": [], "measurements": {}}
    )
    result = {
        "html": str(html_path),
        "viewport": {"width": viewport[0], "height": viewport[1]},
        "errors": static["errors"] + dynamic_result["errors"],
        "warnings": static["warnings"] + dynamic_result["warnings"],
        "error_details": static["error_details"] + dynamic_result["error_details"],
        "warning_details": static["warning_details"] + dynamic_result["warning_details"],
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
    error_details: list[dict] = []
    warning_details: list[dict] = []
    for role in REQUIRED_ROLES:
        if not soup.select(f'[data-role="{role}"]'):
            _add_issue(error_details, errors, "missing-role", f'missing data-role="{role}"', selector=f'[data-role="{role}"]')
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src.startswith(("http://", "https://", "data:")):
            continue
        if src and not (html_path.parent / src).exists():
            _add_issue(error_details, errors, "broken-image", f"broken image: {src}", selector=f'img[src="{src}"]')
    return {"errors": errors, "warnings": warnings, "error_details": error_details, "warning_details": warning_details}


def _playwright_checks(html_path: Path, viewport: tuple[int, int]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    error_details: list[dict] = []
    warning_details: list[dict] = []
    measurements: dict = {}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _add_issue(warning_details, warnings, "dynamic-skipped", "playwright not installed; dynamic layout checks skipped")
        return {"errors": errors, "warnings": warnings, "error_details": error_details, "warning_details": warning_details, "measurements": measurements}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        page.goto(html_path.as_uri(), wait_until="networkidle")
        _wait_for_math(page)
        data = page.evaluate(
            """() => {
              const round = value => Math.round(value * 1000) / 1000;
              const rectOf = el => {
                const r = el.getBoundingClientRect();
                return {x:round(r.x), y:round(r.y), w:round(r.width), h:round(r.height),
                        bottom:round(r.bottom), right:round(r.right)};
              };
              const childOverflow = (el, r) => {
                let left = 0, top = 0, right = 0, bottom = 0;
                for (const child of el.querySelectorAll('*')) {
                  const tag = child.tagName.toLowerCase();
                  if (tag === 'script' || tag === 'style' || tag === 'noscript') continue;
                  const cr = child.getBoundingClientRect();
                  if (cr.width <= 0 || cr.height <= 0) continue;
                  left = Math.max(left, r.x - cr.x);
                  top = Math.max(top, r.y - cr.y);
                  right = Math.max(right, cr.right - r.right);
                  bottom = Math.max(bottom, cr.bottom - r.bottom);
                }
                return {left:round(left), top:round(top), right:round(right), bottom:round(bottom)};
              };
              const box = (sel, label) => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const r = rectOf(el);
                const cs = getComputedStyle(el);
                return {...r, label: label || sel, selector: sel,
                        scrollW: el.scrollWidth, clientW: el.clientWidth,
                        scrollH: el.scrollHeight, clientH: el.clientHeight,
                        overflowX: Math.max(0, el.scrollWidth - el.clientWidth),
                        overflowY: Math.max(0, el.scrollHeight - el.clientHeight),
                        cssOverflowX: cs.overflowX, cssOverflowY: cs.overflowY,
                        childOverflow: childOverflow(el, r)};
              };
              const allBoxes = [];
              const pushAll = (selector, label) => {
                Array.from(document.querySelectorAll(selector)).forEach((el, index) => {
                  const nthLabel = `${label} ${index + 1}`;
                  const nthSelector = `${selector}:nth-of-type(${index + 1})`;
                  const r = rectOf(el);
                  const cs = getComputedStyle(el);
                  allBoxes.push({...r, label: nthLabel, selector: nthSelector,
                    scrollW: el.scrollWidth, clientW: el.clientWidth,
                    scrollH: el.scrollHeight, clientH: el.clientHeight,
                    overflowX: Math.max(0, el.scrollWidth - el.clientWidth),
                    overflowY: Math.max(0, el.scrollHeight - el.clientHeight),
                    cssOverflowX: cs.overflowX, cssOverflowY: cs.overflowY,
                    childOverflow: childOverflow(el, r)});
                });
              };
              pushAll('.text-card', 'text card');
              pushAll('[data-role="figure-card"]', 'figure card');
              pushAll('[data-role="figure-card"] figcaption', 'figure caption');
              pushAll('[data-role="header"]', 'header');
              pushAll('[data-role="meta"]', 'meta');
              pushAll('[data-role="headline"]', 'headline');
              const figs = Array.from(document.querySelectorAll('[data-role="figure-card"]')).map((card, index) => {
                const r = rectOf(card);
                const img = card.querySelector('img');
                const ir = img ? rectOf(img) : null;
                return {index: index + 1, card:r, img: ir ? {...ir, naturalW: img.naturalWidth, naturalH: img.naturalHeight, src: img.getAttribute('src') || ''} : null};
              });
              return {
                bodyScrollW: document.documentElement.scrollWidth,
                bodyScrollH: document.documentElement.scrollHeight,
                viewportW: window.innerWidth,
                viewportH: window.innerHeight,
                poster: box('[data-role="poster"]', 'poster'),
                header: box('[data-role="header"]', 'header'),
                text: box('[data-role="text-column"]', 'text column'),
                figurePanel: box('[data-role="figure-panel"]', 'figure panel'),
                figures: figs,
                boxes: allBoxes
              };
            }"""
        )
        browser.close()
    measurements = data
    if data["bodyScrollW"] > viewport[0] + 2 or data["bodyScrollH"] > viewport[1] + 2:
        _add_issue(error_details, errors, "page-scroll", "page scrolls beyond viewport", overflow_px=max(data["bodyScrollW"] - viewport[0], data["bodyScrollH"] - viewport[1]))
    poster = data.get("poster") or {}
    if poster:
        if abs(poster.get("x", 0)) > CANVAS_TOLERANCE_PX or abs(poster.get("y", 0)) > CANVAS_TOLERANCE_PX:
            _add_issue(error_details, errors, "canvas-position", "poster is not aligned to viewport origin", selector='[data-role="poster"]')
        if abs(poster.get("right", 0) - viewport[0]) > CANVAS_TOLERANCE_PX or abs(poster.get("bottom", 0) - viewport[1]) > CANVAS_TOLERANCE_PX:
            _add_issue(error_details, errors, "canvas-size", "poster does not fill the target viewport", selector='[data-role="poster"]')
    header = data.get("header") or {}
    if header.get("h", 0) > viewport[1] * 0.2:
        _add_issue(error_details, errors, "header-too-tall", "header exceeds 20% of viewport height", selector='[data-role="header"]', overflow_px=header.get("h", 0) - viewport[1] * 0.2)
    text = data.get("text") or {}
    if text and text.get("scrollH", 0) > text.get("clientH", 0) + 2:
        overflow = text.get("scrollH", 0) - text.get("clientH", 0)
        _add_issue(error_details, errors, "text-column-overflow", f"text column overflows by {overflow:.0f}px", selector='[data-role="text-column"]', overflow_px=overflow)
    for item in data.get("boxes") or []:
        label = item.get("label", "element")
        selector = item.get("selector")
        overflow_y = item.get("overflowY", 0)
        overflow_x = item.get("overflowX", 0)
        if label.startswith("text card") and item.get("clientH", 0) < MIN_TEXT_CARD_HEIGHT_PX:
            _add_issue(error_details, errors, "near-zero-region", f"{label} has near-zero usable height", selector=selector)
        if overflow_y > OVERFLOW_TOLERANCE_PX:
            _add_issue(error_details, errors, "content-overflow-y", f"{label} content exceeds by {overflow_y:.0f}px vertically", selector=selector, overflow_px=overflow_y)
        if overflow_x > OVERFLOW_TOLERANCE_PX:
            _add_issue(error_details, errors, "content-overflow-x", f"{label} content exceeds by {overflow_x:.0f}px horizontally", selector=selector, overflow_px=overflow_x)
        child = item.get("childOverflow") or {}
        child_overflow = max(child.get("left", 0), child.get("top", 0), child.get("right", 0), child.get("bottom", 0))
        if child_overflow > 2:
            _add_issue(error_details, errors, "descendant-bounds", f"{label} descendant paint exceeds bounds by {child_overflow:.0f}px", selector=selector, overflow_px=child_overflow)
    for i, fig in enumerate(data.get("figures") or [], 1):
        img = fig.get("img")
        if not img:
            _add_issue(error_details, errors, "missing-figure-image", f"figure card {i} has no image", selector=f'[data-role="figure-card"]:nth-of-type({i})')
            continue
        if img.get("w", 0) <= 1 or img.get("h", 0) <= 1:
            _add_issue(error_details, errors, "blank-figure-image", f"figure card {i} image renders blank", selector=f'[data-role="figure-card"]:nth-of-type({i}) img')
            continue
        if img.get("naturalW", 0) <= 0 and not img.get("src", "").lower().endswith(".svg"):
            _add_issue(error_details, errors, "broken-figure-image", f"figure card {i} image has no natural size", selector=f'[data-role="figure-card"]:nth-of-type({i}) img')
        if img["w"] < 360 or img["h"] < 220:
            _add_issue(warning_details, warnings, "tiny-figure-image", f"figure card {i} image may be too small ({img['w']:.0f}x{img['h']:.0f}px)", selector=f'[data-role="figure-card"]:nth-of-type({i}) img')
    return {"errors": errors, "warnings": warnings, "error_details": error_details, "warning_details": warning_details, "measurements": measurements}


def diagnose_result(result: dict) -> list[str]:
    suggestions: list[str] = []
    details = result.get("error_details", [])
    overflow_details = [item for item in details if item.get("overflow_px")]
    if any("text card 1" in item.get("message", "") for item in details):
        suggestions.append("Shorten Background/Knowledge gap first; they are consuming too much of the left column.")
    if any("text card 3" in item.get("message", "") for item in details):
        suggestions.append("Restore space for Key results by trimming earlier text cards or reducing from four figures only if one figure is weak.")
    if any(item.get("kind") == "near-zero-region" for item in details):
        suggestions.append("A grid region has collapsed; rebalance grid rows before rendering.")
    if any("figure caption" in item.get("message", "") for item in details):
        suggestions.append("Trim figure captions to one short takeaway sentence each.")
    if overflow_details:
        worst = max(overflow_details, key=lambda item: item.get("overflow_px") or 0)
        suggestions.append(f"Largest measured overflow: {worst.get('message')}.")
    fig_count = len((result.get("measurements") or {}).get("figures") or [])
    if fig_count >= 4 and overflow_details:
        suggestions.append("If one figure is secondary, switch to the 3-figure hero layout instead of leaving an empty 2x2 slot.")
    if not suggestions and result.get("warnings"):
        suggestions.append("Warnings remain; inspect figure size and caption readability before final render.")
    if not suggestions:
        suggestions.append("No deterministic layout problems found.")
    return suggestions


def _add_issue(
    details: list[dict],
    messages: list[str],
    kind: str,
    message: str,
    *,
    selector: str | None = None,
    overflow_px: float | int | None = None,
) -> None:
    item = {"kind": kind, "message": message}
    if selector:
        item["selector"] = selector
    if overflow_px is not None:
        item["overflow_px"] = round(float(overflow_px), 3)
    details.append(item)
    messages.append(message)

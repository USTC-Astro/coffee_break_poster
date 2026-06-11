from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from check import check_html, diagnose_result
import cbp as cbp_module
from config import resolve_mineru_config
from inputs import _ingest_local, ingest
from mineru import _download_cloud_result, convert_pdf
from paper_inspect import inspect_paper
import render as render_module
from scaffold import scaffold


def test_ingest_existing_mineru_dir(tmp_path: Path) -> None:
    paper_dir = ingest(ROOT / "examples" / "mineru_sample", tmp_path)

    assert (paper_dir / "paper.md").exists()
    assert (paper_dir / "images" / "fig1.svg").exists()
    source = json.loads((paper_dir / "source.json").read_text(encoding="utf-8"))
    assert source["kind"] == "mineru_dir"


def test_inspect_and_scaffold_sample(tmp_path: Path) -> None:
    paper_dir = ingest(ROOT / "examples" / "mineru_sample", tmp_path)
    inventory = inspect_paper(paper_dir, paper_dir / "inspect.json")

    assert inventory["word_count"] > 20
    assert len(inventory["referenced_images"]) == 2
    assert inventory["referenced_images"][0]["width"] > 0

    html_path = scaffold(
        paper_dir=paper_dir,
        template=ROOT / "templates" / "screen_16x9_figure_focus.html",
        overwrite=True,
    )
    html = html_path.read_text(encoding="utf-8")

    assert 'data-role="poster"' in html
    assert "Helvetica" in html
    assert "text-transform: uppercase" in html
    assert "MathJax" in html
    assert "knowledge-gap" in html
    assert "Fig. 1." in html
    assert (paper_dir / "assets" / "fig1.svg").exists()


def _paper_with_figures(tmp_path: Path, count: int) -> Path:
    paper_dir = tmp_path / "paper"
    image_dir = paper_dir / "images"
    image_dir.mkdir(parents=True)
    md_parts = ["# Sample Paper\n"]
    for idx in range(1, count + 1):
        (image_dir / f"fig{idx}.svg").write_text(
            '<svg width="800" height="450" viewBox="0 0 800 450" xmlns="http://www.w3.org/2000/svg"></svg>',
            encoding="utf-8",
        )
        md_parts.append(f"![figure {idx}](images/fig{idx}.svg)\n")
    paper_dir.joinpath("paper.md").write_text("\n".join(md_parts), encoding="utf-8")
    return paper_dir


def test_scaffold_one_figure_uses_solo_layout(tmp_path: Path) -> None:
    paper_dir = _paper_with_figures(tmp_path, 1)

    html_path = scaffold(paper_dir, overwrite=True, figure_count=1)
    html = html_path.read_text(encoding="utf-8")

    assert 'data-layout="solo"' in html
    assert html.count('data-role="figure-card"') == 1


def test_scaffold_two_figures_uses_hero_support_layout(tmp_path: Path) -> None:
    paper_dir = _paper_with_figures(tmp_path, 2)

    html_path = scaffold(paper_dir, overwrite=True, figure_count=2)
    html = html_path.read_text(encoding="utf-8")

    assert 'data-layout="hero-1"' in html
    assert html.count('data-role="figure-card"') == 2


def test_scaffold_three_figures_uses_hero_layout(tmp_path: Path) -> None:
    paper_dir = _paper_with_figures(tmp_path, 3)

    html_path = scaffold(paper_dir, overwrite=True, figure_count=3)
    html = html_path.read_text(encoding="utf-8")

    assert 'data-layout="hero-2"' in html
    assert html.count('data-role="figure-card"') == 3


def test_scaffold_screen_format_uses_default_template(tmp_path: Path) -> None:
    paper_dir = _paper_with_figures(tmp_path, 1)

    html_path = scaffold(paper_dir, overwrite=True, figure_count=1, format="screen")
    html = html_path.read_text(encoding="utf-8")

    assert "--canvas-w: 1920px" in html
    assert "Background" in html


def test_scaffold_phone_one_figure_uses_phone_template(tmp_path: Path) -> None:
    paper_dir = _paper_with_figures(tmp_path, 1)

    html_path = scaffold(paper_dir, overwrite=True, figure_count=1, format="phone")
    html = html_path.read_text(encoding="utf-8")

    assert "--canvas-w: 1080px" in html
    assert "--canvas-h: 1920px" in html
    assert "Why it matters" in html
    assert 'data-layout="solo"' in html
    assert html.count('data-role="figure-card"') == 1


def test_scaffold_phone_two_figures_uses_support_layout(tmp_path: Path) -> None:
    paper_dir = _paper_with_figures(tmp_path, 2)

    html_path = scaffold(paper_dir, overwrite=True, figure_count=2, format="phone")
    html = html_path.read_text(encoding="utf-8")

    assert 'data-layout="hero-1"' in html
    assert html.count('data-role="figure-card"') == 2


def test_scaffold_phone_three_figures_uses_two_support_layout(tmp_path: Path) -> None:
    paper_dir = _paper_with_figures(tmp_path, 3)

    html_path = scaffold(paper_dir, overwrite=True, figure_count=3, format="phone")
    html = html_path.read_text(encoding="utf-8")

    assert 'data-layout="hero-2"' in html
    assert html.count('data-role="figure-card"') == 3


def test_scaffold_template_overrides_format(tmp_path: Path) -> None:
    paper_dir = _paper_with_figures(tmp_path, 1)
    template = tmp_path / "custom.html"
    template.write_text("<html><body>CUSTOM {{PAPER_TITLE}} {{FIGURES}}</body></html>", encoding="utf-8")

    html_path = scaffold(paper_dir, template=template, overwrite=True, figure_count=1, format="phone")
    html = html_path.read_text(encoding="utf-8")

    assert "CUSTOM Sample Paper" in html
    assert "--canvas-w: 1080px" not in html


def test_render_blocks_failed_layout_before_outputs(tmp_path: Path, monkeypatch) -> None:
    html_path = tmp_path / "poster.html"
    html_path.write_text("<main></main>", encoding="utf-8")

    def fake_check(html, *, json_out=None, viewport=(1920, 1080)):
        if json_out:
            Path(json_out).write_text('{"ok": false}', encoding="utf-8")
        return {"errors": ["text card 1 content exceeds by 80px vertically"], "warnings": []}

    monkeypatch.setattr(render_module, "check_html", fake_check)

    try:
        render_module.render(html_path, png=True)
    except RuntimeError as exc:
        assert "layout check failed" in str(exc)
    else:
        raise AssertionError("render should fail before writing outputs")

    assert not (tmp_path / "poster_preview.png").exists()
    assert (tmp_path / "layout.json").exists()


def test_cli_check_phone_format_uses_phone_viewport(tmp_path: Path, monkeypatch) -> None:
    html_path = tmp_path / "poster.html"
    html_path.write_text("<main></main>", encoding="utf-8")
    seen = {}

    def fake_check(html, *, json_out=None, viewport=(1920, 1080), dynamic=True):
        seen["viewport"] = viewport
        seen["dynamic"] = dynamic
        if json_out:
            Path(json_out).write_text(json.dumps({"ok": True, "viewport": {"width": viewport[0], "height": viewport[1]}}), encoding="utf-8")
        return {"errors": [], "warnings": []}

    monkeypatch.setattr(cbp_module, "check_html", fake_check)

    rc = cbp_module.main(["check", str(html_path), "--format", "phone", "--json-out", str(tmp_path / "layout.json")])

    assert rc == 0
    assert seen == {"viewport": (1080, 1920), "dynamic": True}
    result = json.loads((tmp_path / "layout.json").read_text(encoding="utf-8"))
    assert result["viewport"] == {"width": 1080, "height": 1920}


def test_cli_check_viewport_overrides_format(tmp_path: Path, monkeypatch) -> None:
    html_path = tmp_path / "poster.html"
    html_path.write_text("<main></main>", encoding="utf-8")
    seen = {}

    def fake_check(html, *, json_out=None, viewport=(1920, 1080), dynamic=True):
        seen["viewport"] = viewport
        return {"errors": [], "warnings": []}

    monkeypatch.setattr(cbp_module, "check_html", fake_check)

    rc = cbp_module.main(["check", str(html_path), "--format", "phone", "--viewport", "800x1200"])

    assert rc == 0
    assert seen["viewport"] == (800, 1200)


def test_cli_render_phone_format_passes_phone_viewport(tmp_path: Path, monkeypatch) -> None:
    html_path = tmp_path / "poster.html"
    html_path.write_text("<main></main>", encoding="utf-8")
    seen = {}

    def fake_render(html, *, png=True, pdf=False, viewport=(1920, 1080), force=False):
        seen.update({"png": png, "pdf": pdf, "viewport": viewport, "force": force})
        layout = tmp_path / "layout.json"
        png_path = tmp_path / "poster_preview.png"
        pdf_path = tmp_path / "poster.pdf"
        layout.write_text("{}", encoding="utf-8")
        png_path.write_text("png", encoding="utf-8")
        pdf_path.write_text("pdf", encoding="utf-8")
        return {"layout": str(layout), "png": str(png_path), "pdf": str(pdf_path)}

    monkeypatch.setattr(cbp_module, "render", fake_render)

    rc = cbp_module.main(["render", str(html_path), "--format", "phone", "--png", "--pdf"])

    assert rc == 0
    assert seen == {"png": True, "pdf": True, "viewport": (1080, 1920), "force": False}
    assert (tmp_path / "layout.json").exists()
    assert (tmp_path / "poster_preview.png").exists()
    assert (tmp_path / "poster.pdf").exists()


def test_diagnose_recommends_three_figure_layout_for_overflow() -> None:
    result = {
        "warnings": [],
        "measurements": {"figures": [{}, {}, {}, {}]},
        "error_details": [
            {"kind": "content-overflow-y", "message": "text card 1 content exceeds by 80px vertically", "overflow_px": 80},
            {"kind": "near-zero-region", "message": "text card 3 has near-zero usable height"},
        ],
    }

    suggestions = diagnose_result(result)

    assert any("Background" in item for item in suggestions)
    assert any("3-figure hero layout" in item for item in suggestions)


def test_static_check_catches_broken_images(tmp_path: Path) -> None:
    html_path = tmp_path / "poster.html"
    html_path.write_text(
        '<main data-role="poster"><img src="missing.png" alt="missing"></main>',
        encoding="utf-8",
    )

    result = check_html(html_path, dynamic=False)

    assert result["ok"] is False
    assert any("broken image" in item for item in result["errors"])


def test_cli_help() -> None:
    proc = subprocess.run(
        [sys.executable, str(TOOLS / "cbp.py"), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Coffee-break poster tools" in proc.stdout


def test_config_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("MINERU_API_KEY", "env-key")
    cfg = resolve_mineru_config()

    assert cfg.api_key == "env-key"


def test_convert_pdf_requires_cloud_key(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    cfg = resolve_mineru_config()
    cfg.api_key = ""

    try:
        convert_pdf(pdf_path, tmp_path / "out", cfg)
    except RuntimeError as exc:
        assert "MinerU cloud API key missing" in str(exc)
    else:
        raise AssertionError("convert_pdf should require a cloud API key")


def test_ingest_local_pdf_skips_self_copy(tmp_path: Path, monkeypatch) -> None:
    paper_dir = tmp_path / "arxiv-2605-21574"
    paper_dir.mkdir()
    pdf_path = paper_dir / "arxiv-2605.21574.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    def fake_convert(pdf_path_arg: Path, out_dir_arg: Path, cfg) -> Path:
        assert pdf_path_arg == pdf_path
        assert out_dir_arg == paper_dir
        md_path = out_dir_arg / "paper.md"
        md_path.write_text("# Title\n", encoding="utf-8")
        return md_path

    monkeypatch.setattr("inputs.convert_pdf", fake_convert)

    result = _ingest_local(pdf_path, tmp_path, resolve_mineru_config())

    assert result == paper_dir
    assert (paper_dir / "paper.md").exists()
    source = json.loads((paper_dir / "source.json").read_text(encoding="utf-8"))
    assert source["kind"] == "pdf"


def test_download_cloud_result_prefers_md_content(tmp_path: Path) -> None:
    item = {"md_content": "# Title\nhello"}

    md = _download_cloud_result(item, tmp_path)

    assert md == "# Title\nhello"


def test_download_cloud_result_supports_md_url(tmp_path: Path, monkeypatch) -> None:
    class FakeResp:
        status_code = 200
        text = "# From URL\n"

    monkeypatch.setattr("mineru._direct_get", lambda url, timeout: FakeResp())

    md = _download_cloud_result({"md_url": "https://example.invalid/paper.md"}, tmp_path)

    assert md == "# From URL\n"


def test_download_cloud_result_supports_full_zip_url(tmp_path: Path, monkeypatch) -> None:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("paper.md", "# From Zip\n")
        zf.writestr("images/fig1.png", b"fake-image")

    class FakeResp:
        status_code = 200
        content = buf.getvalue()

    monkeypatch.setattr("mineru._direct_get", lambda url, timeout: FakeResp())

    md = _download_cloud_result({"full_zip_url": "https://example.invalid/result.zip"}, tmp_path)

    assert md == "# From Zip\n"
    assert (tmp_path / "images" / "fig1.png").read_bytes() == b"fake-image"

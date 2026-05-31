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

from check import check_html
from config import resolve_mineru_config
from inputs import ingest
from mineru import _download_cloud_result, convert_pdf
from paper_inspect import inspect_paper
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

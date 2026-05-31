from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import requests

try:
    from .config import MineruConfig
except ImportError:
    from config import MineruConfig


def check_local(endpoint: str) -> bool:
    try:
        resp = requests.get(f"{endpoint.rstrip('/')}/docs", timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def convert_pdf(pdf_path: Path, out_dir: Path, cfg: MineruConfig) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not cfg.api_key:
        raise RuntimeError("MinerU cloud API key missing: set --mineru-api-key, MINERU_API_KEY, or config.local.yaml mineru.api_key")
    return _convert_cloud(pdf_path, out_dir, cfg)


def _convert_local(pdf_path: Path, out_dir: Path, endpoint: str) -> Path:
    md_path = out_dir / "paper.md"
    form_data = {
        "backend": (None, "pipeline"),
        "parse_method": (None, "auto"),
        "formula_enable": (None, "true"),
        "table_enable": (None, "true"),
        "return_md": (None, "true"),
        "return_images": (None, "true"),
        "lang_list": (None, "en"),
    }
    with open(pdf_path, "rb") as f:
        files = {"files": (pdf_path.name, f, "application/pdf")}
        resp = requests.post(f"{endpoint.rstrip('/')}/file_parse", files={**files, **form_data}, timeout=600)
    resp.raise_for_status()
    data = resp.json()
    md = _extract_md(data)
    if not md:
        raise RuntimeError("MinerU local response did not contain markdown")
    md_path.write_text(md, encoding="utf-8")
    return md_path


def _convert_cloud(pdf_path: Path, out_dir: Path, cfg: MineruConfig) -> Path:
    md_path = out_dir / "paper.md"
    headers = {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"}
    payload = {
        "files": [{"name": pdf_path.name, "data_id": pdf_path.stem}],
        "model_version": "pipeline",
        "enable_formula": True,
        "enable_table": True,
        "language": "en",
    }
    try:
        resp = requests.post(f"{cfg.cloud_url.rstrip('/')}/file-urls/batch", headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        raise RuntimeError(f"MinerU cloud request failed: {exc}") from exc
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"MinerU cloud error: {data.get('msg', 'unknown')}")
    batch = data.get("data", {})
    batch_id = batch.get("batch_id")
    upload_url = (batch.get("file_urls") or [""])[0]
    if not batch_id or not upload_url:
        raise RuntimeError("MinerU cloud did not return batch_id/upload_url")
    try:
        with open(pdf_path, "rb") as f:
            put = _direct_put(upload_url, data=f, timeout=120)
    except requests.RequestException as exc:
        raise RuntimeError(f"MinerU cloud upload failed: {exc}") from exc
    if put.status_code not in (200, 201):
        raise RuntimeError(f"MinerU cloud upload failed: HTTP {put.status_code}")
    deadline = time.time() + 900
    while time.time() < deadline:
        time.sleep(5)
        try:
            poll = requests.get(
                f"{cfg.cloud_url.rstrip('/')}/extract-results/batch/{batch_id}",
                headers={"Authorization": f"Bearer {cfg.api_key}"},
                timeout=30,
            )
            poll.raise_for_status()
            pdata = poll.json()
        except requests.RequestException:
            continue
        except ValueError:
            continue
        if pdata.get("code") != 0:
            continue
        results = pdata.get("data", {}).get("extract_result", [])
        if not results:
            continue
        item = results[0]
        if item.get("state") == "failed":
            raise RuntimeError(f"MinerU cloud parse failed: {item.get('err_msg', 'unknown')}")
        if item.get("state") != "done":
            continue
        md = _download_cloud_result(item, out_dir)
        if md is None:
            raise RuntimeError(f"MinerU cloud result did not contain markdown. Response keys: {list(item.keys())}")
        md_path.write_text(md, encoding="utf-8")
        return md_path
    raise RuntimeError("MinerU cloud parse timed out")


def _direct_get(url: str, *, timeout: int):
    # MinerU CDN downloads can fail through user-configured proxies.
    sess = requests.Session()
    sess.trust_env = False
    try:
        return sess.get(url, timeout=timeout)
    finally:
        sess.close()


def _direct_put(url: str, data, *, timeout: int):
    # Signed MinerU upload URLs can also hang or fail through user-configured proxies.
    sess = requests.Session()
    sess.trust_env = False
    try:
        return sess.put(url, data=data, timeout=timeout)
    finally:
        sess.close()


def _download_cloud_result(item: dict, out_dir: Path) -> str | None:
    md = item.get("md_content")
    if isinstance(md, str) and md.strip():
        return md

    zip_url = item.get("full_zip_url")
    if zip_url:
        try:
            resp = _direct_get(zip_url, timeout=120)
            if resp.status_code == 200:
                md_content = None
                with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                    for name in zf.namelist():
                        if name.endswith("/"):
                            continue
                        if name.endswith(".md"):
                            md_content = zf.read(name).decode("utf-8")
                        else:
                            dest = out_dir / name
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(zf.read(name))
                if isinstance(md_content, str) and md_content.strip():
                    return md_content
        except Exception:
            pass

    md_url = item.get("md_url")
    if md_url:
        try:
            resp = _direct_get(md_url, timeout=60)
            if resp.status_code == 200 and resp.text.strip():
                return resp.text
        except Exception:
            pass

    return None


def _extract_md(data) -> str:
    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, dict):
            for entry in results.values():
                if isinstance(entry, dict) and isinstance(entry.get("md_content"), str):
                    return entry["md_content"]
        for key in ("md_content", "md", "markdown", "content"):
            if isinstance(data.get(key), str):
                return data[key]
    return ""

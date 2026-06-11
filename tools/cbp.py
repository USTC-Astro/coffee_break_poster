#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

try:
    from .check import check_html, diagnose_result
    from .config import resolve_mineru_config
    from .inputs import ingest
    from .paper_inspect import inspect_paper
    from .render import render
    from .scaffold import scaffold
except ImportError:
    from check import check_html, diagnose_result
    from config import resolve_mineru_config
    from inputs import ingest
    from paper_inspect import inspect_paper
    from render import render
    from scaffold import scaffold


FORMAT_VIEWPORTS = {
    "screen": (1920, 1080),
    "phone": (1080, 1920),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cbp", description="Coffee-break poster tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def mineru_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--mineru-endpoint")
        p.add_argument("--mineru-cloud-url")
        p.add_argument("--mineru-api-key")
        p.add_argument("--force-cloud", action="store_true")

    p_ingest = sub.add_parser("ingest", help="normalize input into paper.md + images")
    p_ingest.add_argument("input")
    p_ingest.add_argument("--workdir")
    mineru_args(p_ingest)

    p_inspect = sub.add_parser("inspect", help="inspect a MinerU-style paper directory")
    p_inspect.add_argument("paper_dir")
    p_inspect.add_argument("--json", action="store_true")

    p_scaffold = sub.add_parser("scaffold", help="create poster.html from template")
    p_scaffold.add_argument("paper_dir")
    p_scaffold.add_argument("--template")
    p_scaffold.add_argument("--format", choices=tuple(FORMAT_VIEWPORTS), default="screen")
    p_scaffold.add_argument("--overwrite", action="store_true")
    p_scaffold.add_argument("--figure-count", type=int, choices=(1, 2, 3, 4), default=4)

    p_check = sub.add_parser("check", help="measure one-screen poster layout")
    p_check.add_argument("poster_html")
    p_check.add_argument("--json-out")
    p_check.add_argument("--format", choices=tuple(FORMAT_VIEWPORTS), default="screen")
    p_check.add_argument("--viewport")
    p_check.add_argument("--static-only", action="store_true", help="skip Playwright layout measurements")

    p_diagnose = sub.add_parser("diagnose", help="explain layout problems and suggest fixes")
    p_diagnose.add_argument("poster_html")
    p_diagnose.add_argument("--format", choices=tuple(FORMAT_VIEWPORTS), default="screen")
    p_diagnose.add_argument("--viewport")
    p_diagnose.add_argument("--json", action="store_true")

    p_render = sub.add_parser("render", help="render poster HTML to PNG/PDF")
    p_render.add_argument("poster_html")
    p_render.add_argument("--png", action="store_true")
    p_render.add_argument("--pdf", action="store_true")
    p_render.add_argument("--format", choices=tuple(FORMAT_VIEWPORTS), default="screen")
    p_render.add_argument("--viewport")
    p_render.add_argument("--force", action="store_true", help="render even if layout checks fail")

    p_build = sub.add_parser("build", help="run deterministic ingest, inspect, scaffold, check")
    p_build.add_argument("input")
    p_build.add_argument("--workdir")
    mineru_args(p_build)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "ingest":
            paper_dir = ingest(args.input, args.workdir, resolve_mineru_config(args))
            print(paper_dir)
            return 0
        if args.cmd == "inspect":
            result = inspect_paper(args.paper_dir)
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _summary(result))
            return 0
        if args.cmd == "scaffold":
            print(scaffold(args.paper_dir, args.template, overwrite=args.overwrite, figure_count=args.figure_count, format=args.format))
            return 0
        if args.cmd == "check":
            result = check_html(
                args.poster_html,
                json_out=args.json_out,
                viewport=_viewport_for_args(args),
                dynamic=not args.static_only,
            )
            print(_check_summary(result))
            return 1 if result["errors"] else 0
        if args.cmd == "diagnose":
            result = check_html(args.poster_html, viewport=_viewport_for_args(args))
            suggestions = diagnose_result(result)
            if args.json:
                print(json.dumps({"ok": result["ok"], "suggestions": suggestions, "errors": result["errors"], "warnings": result["warnings"]}, ensure_ascii=False, indent=2))
            else:
                print(_check_summary(result))
                for suggestion in suggestions:
                    print(f"SUGGEST: {suggestion}")
            return 1 if result["errors"] else 0
        if args.cmd == "render":
            outputs = render(args.poster_html, png=args.png or not args.pdf, pdf=args.pdf, viewport=_viewport_for_args(args), force=args.force)
            print(json.dumps(outputs, indent=2))
            return 0
        if args.cmd == "build":
            paper_dir = ingest(args.input, args.workdir, resolve_mineru_config(args))
            inspect_paper(paper_dir)
            poster = scaffold(paper_dir)
            result = check_html(poster, json_out=paper_dir / "layout.json")
            print(_check_summary(result))
            return 1 if result["errors"] else 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


def _viewport(value: str) -> tuple[int, int]:
    w, h = value.lower().split("x", 1)
    return int(w), int(h)


def _viewport_for_args(args: argparse.Namespace) -> tuple[int, int]:
    if args.viewport:
        return _viewport(args.viewport)
    return FORMAT_VIEWPORTS[args.format]


def _summary(result: dict) -> str:
    return f"{result.get('title') or '(untitled)'}\nsections: {len(result.get('sections', []))}\nfigures: {len(result.get('figures', []))}\nwarnings: {len(result.get('warnings', []))}"


def _check_summary(result: dict) -> str:
    lines = []
    lines.append("PASS" if not result["errors"] else "FAIL")
    for err in result["errors"]:
        lines.append(f"ERROR: {err}")
    for warn in result["warnings"]:
        lines.append(f"WARN: {warn}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

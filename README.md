# coffee_break_poster

This is a `codex` skill to convert any paper (local `.pdf` / arXiv DOI) to a quick advertising-style poster, with a screen-adapted 16:9 layout suitable for inspiration-driven discussion during a coffee break. The key goal of `coffee_break_poster` is not to overwhelm the audience with dauntingly detailed methodological illustrations, but to hook a broad astronomy audience with the background and knowledge gap (*why people should care*) in ~30s, convey the key knowledge increment (*what is the key selling point*) in ~60s, and leave them remembering the figures that support the findings in ~60s.

The idea of `coffee_break_poster` was born during a weekly coffee break at USTC. The key features include automatic `.pdf` to AI-favored `.md` conversion with [MinerU](https://mineru.net), astrophysics-centered LLM summarizing, a screen-adapted poster layout (inspired by [arxiv_display](https://github.com/mpi-astronomy/arxiv_display)), and iterative text / figure size adjustment for optimal layout (inspired by [posterly](https://github.com/Chenruishuo/posterly/tree/main/)).

# Showcase

The repository includes a small MinerU-style sample in `examples/mineru_sample/`. A normal run produces a single-screen `poster.html` plus rendered preview assets in `work/<paper-slug>/`.

The default poster shape is:

- one 16:9 screen
- a compact text column on the left
- `2-4` figures on the right
- text blocks for `Background`, `Knowledge gap`, `What this paper is selling`, and `Key results to remember`

# Installation

Clone the repo and install it as a normal Python package:

```bash
git clone <repo-url> ~/.codex/skills/coffee_break_poster
cd ~/.codex/skills/coffee_break_poster
python -m pip install .
```

This installs the `cbp` CLI:

```bash
cbp --help
```

Install browser support once for layout checks and rendering:

```bash
python -m playwright install chromium
```

For development:

```bash
python -m pip install -e .[dev]
```

# Configuration

`config.yaml` is a tracked sample file. Runtime config is still read from `config.local.yaml` and environment variables.

Create your local config like this:

```bash
cp config.yaml config.local.yaml
```

Then edit `config.local.yaml` and fill in your own MinerU settings:

- `mineru.endpoint`: local MinerU service endpoint, default `http://localhost:8000`
- `mineru.cloud_url`: MinerU cloud API base URL
- `mineru.api_key`: your MinerU cloud API key

Environment variables still override local config:

- `MINERU_ENDPOINT`
- `MINERU_CLOUD_URL`
- `MINERU_API_KEY`

If you only work from an existing MinerU-style directory, you do not need a MinerU API key.

# Usage

You can use this repo in two complementary ways:

- as a Codex skill for the editorial/scientific poster writing
- as the `cbp` deterministic CLI for ingest, inspection, scaffolding, checking, and rendering

## Supported inputs

`cbp ingest` accepts four input shapes:

1. a MinerU-style directory containing `paper.md` and `images/`This is a `codex` skill to convert any paper (local `.pdf` / arxiv doi) to a quick advertising-style poster, with screen-adapted 16:9 layout and suitable for inspiration-driven discussion during a coffee break. The key goal of `coffee_break_poster` is not to overwhelm audience with the dauntingly detailed methodological illustrations, but hooks general-astro-people's interest in the field including background and knowledge gap (*why people should care*) in ~30s, grasps the key knowledge increment (*what is the key selling point*) in ~60s, and remembers key figures supporting their findings in ~60s. 

The idea of `coffee_break_poster` was born during a coffee break, held weekly at USTC. The key features include automatic `.pdf` to AI-favored `.md` format with [MinerU](https://mineru.net), astrophysics-centered LLM summarizing, screen-adapted poster layout (inspired from [arxiv_display](https://github.com/mpi-astronomy/arxiv_display)), and iterative text / figure size adjustment for optimal layout (inspired from [posterly](https://github.com/Chenruishuo/posterly/tree/main/)).

2. a local `.pdf`
3. an arXiv identifier such as `2401.01234` or `arxiv:2401.01234`
4. a direct PDF URL

## Typical workflow

Normalize input into a working paper directory:

```bash
cbp ingest INPUT --workdir work
```

Inspect the paper inventory:

```bash
cbp inspect work/<paper-slug> --json
```

Scaffold a starter poster:

```bash
cbp scaffold work/<paper-slug>
```

Check one-screen layout:

```bash
cbp check work/<paper-slug>/poster.html --json-out work/<paper-slug>/layout.json
```

Render PNG and PDF outputs:

```bash
cbp render work/<paper-slug>/poster.html --png --pdf
```

There is also a convenience command for the deterministic setup phase:

```bash
cbp build INPUT --workdir work
```

`build` runs `ingest`, `inspect`, `scaffold`, and `check` in sequence, then leaves you with a starter poster to edit.

## Example input modes

Use an existing MinerU directory:

```bash
cbp ingest examples/mineru_sample --workdir work
```

Use a local PDF:

```bash
cbp ingest ~/papers/my-paper.pdf --workdir work
```

Use an arXiv paper:

```bash
cbp ingest 2401.01234 --workdir work
```

Use a direct PDF URL:

```bash
cbp ingest https://arxiv.org/pdf/2401.01234.pdf --workdir work
```

## How the skill is meant to be used

The CLI handles deterministic steps:

- normalize the paper into `paper.md + images/`
- inspect sections, images, and figure candidates
- scaffold a 16:9 HTML poster
- check overflow and broken assets
- render preview outputs

The Codex skill handles the non-deterministic editorial work:

- identify the main selling point
- write the title, subtitle, and text blocks
- choose the figures worth remembering
- trim or rewrite content until the layout works on one screen

# Skill layout and how it works

The deterministic tools live in `tools/`; templates live in `templates/`; generated posters should go under `work/` or a user-provided work directory.

Typical flow:

```bash
python tools/cbp.py ingest examples/mineru_sample --workdir work
python tools/cbp.py inspect work/mineru-sample --json
python tools/cbp.py scaffold work/mineru-sample
python tools/cbp.py check work/mineru-sample/poster.html --json-out work/mineru-sample/layout.json
python tools/cbp.py render work/mineru-sample/poster.html --png
```

The same flow via the installed CLI:

```bash
cbp ingest examples/mineru_sample --workdir work
cbp inspect work/mineru-sample --json
cbp scaffold work/mineru-sample
cbp check work/mineru-sample/poster.html --json-out work/mineru-sample/layout.json
cbp render work/mineru-sample/poster.html --png
```

## Repository layout

- `tools/`: deterministic CLI implementation and helpers
- `templates/`: HTML poster templates
- `examples/`: sample MinerU-style input
- `tests/`: regression tests for ingest, config, scaffold, and check behavior
- `work/`: generated local outputs
- `SKILL.md`: Codex skill instructions and editorial guidance

## Development and testing

Run the test suite with:

```bash
pytest
```

Useful checks while iterating on the toolchain:

```bash
cbp --help
cbp inspect examples/mineru_sample --json
cbp build examples/mineru_sample --workdir work
```

## Notes

- `config.local.yaml` is intentionally ignored by git because it can contain local endpoints and API keys.
- `config.yaml` is only a committed sample file. Copy it to `config.local.yaml` before editing.
- The scaffolded `poster.html` is a starting point, not a final product. Expect to rewrite text, pick figures, and rerun `cbp check` until the layout is clean.

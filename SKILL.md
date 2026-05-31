---
name: coffee_break_poster
description: Create a one-screen astro coffee-break poster from a MinerU-style paper directory, PDF, arXiv URL, or direct PDF URL. Use the deterministic tools under tools/ for ingest, inspection, layout checks, and rendering; use the agent for summarization, figure choice, narrative design, and HTML edits.
---

# Coffee Break Poster

Create a single-screen, figure-forward astro coffee-break poster.

This skill is for **quick arXiv sharing during a coffee break, journal club, seminar, or hallway discussion**. The goal is not to reproduce the paper in miniature. The goal is to make people stop, look, and remember **why the paper is interesting, what it is claiming, and what the take-away is**.

Default audience: **broad astronomy readers**. Unless the user explicitly asks otherwise, do not optimize for specialists only.

## Core Product Goal

The poster should work as a **fast visual pitch** for the paper:

- A reader should understand the main point in **15-30 seconds**.
- The poster should be **interesting before it is exhaustive**.
- The main intellectual work is to surface the **selling point / take-away / why this matters**, not to restate method details.
- Figures should carry most of the information; text should guide attention and interpretation.

Do **not** turn the poster into:

- a technical review
- a section-by-section paper summary
- a methodology-heavy note
- a wall of text with figures pasted in as decoration

## Work Directory

- If the user provides a work directory, use it.
- Otherwise use `/Users/chensj/repository/coffee_break_poster/work/<paper_slug>/`.
- Do not write generated posters into an installed skill directory.

## Prerequisite

This skill assumes the `cbp` CLI is available on `PATH` via a normal package install or editable install of this repository.

## Expected Output

Produce a **single-screen 16:9 HTML poster** that can be checked and rendered to PNG/PDF.

The default poster structure has exactly these text blocks:

1. `Background`
2. `Knowledge gap`
3. `What this paper is selling`
4. `Key results to remember`

plus **2-4 figures** with short captions.

In practice, the left text column should read like one compact argument:

1. Why should people care?
2. What was missing before this paper?
3. What is this paper claiming to add?
4. What evidence makes that claim worth remembering?

## Workflow

### 1. Normalize input

```bash
cbp ingest INPUT --workdir work
```

### 2. Inspect deterministic paper inventory

```bash
cbp inspect PAPER_DIR --json
```

Use this to inspect sections, image files, dimensions, and candidate captions. This command does **not** summarize the paper for you.

### 3. Read only what you need, then make the scientific/editorial choices

Read `paper.md` selectively. Do not dump or paraphrase the whole paper. Focus on:

- the abstract and conclusion
- the few paragraphs needed to understand the central claim
- the local context around the figures you may use

Then make the poster-level choices:

- Write a **headline** that states what we learn from the paper, not just the topic.
- Write a **subtitle** that frames the interesting astrophysical stake or hook.
- Fill the text blocks so they form one coherent story.
- Choose **2-4 figures**, usually **2-3 strong ones** rather than filling slots mechanically.
- Keep methods short unless they are essential for trust.

### 4. Scaffold and edit

```bash
cbp scaffold PAPER_DIR
```

Edit `poster.html` directly. The default template is 16:9, with text on the left and figures on the right.

### 5. Check and iterate

```bash
cbp check PAPER_DIR/poster.html --json-out PAPER_DIR/layout.json
```

If the check reports overflow, tiny figures, broken images, or blank figure area, edit `poster.html` and rerun. The tools measure layout; the agent must adapt content, figure choice, captions, and CSS.

### 6. Render

```bash
cbp render PAPER_DIR/poster.html --png --pdf
```

## Editorial Rules

### Headline

The headline should say **what the paper teaches us**.

Good headline properties:

- claim-like rather than topic-like
- short enough to scan quickly
- memorable to a non-specialist astro reader
- anchored in the paper's strongest knowledge increment

Avoid headlines that are only:

- the paper title rewritten
- a vague topic label
- method-first framing when the real point is a scientific result

### Subtitle

The subtitle should be a short hook, usually one sentence.

Use it to answer one of these:

- why this result is surprising
- what larger problem it connects to
- what kind of evidence makes the paper interesting

Do not use the subtitle for a long abstract-like summary.

### Background

`Background` answers:

- why should a broad astro audience care?
- what bigger astrophysical question is this connected to?

Do **not** lead with survey names, sample sizes, instrument minutiae, or a chain of technical qualifiers unless those are the actual hook.

### Knowledge gap

`Knowledge gap` should be the **precise missing piece** that motivates the paper.

It must be tightly linked to the background. A good gap sharpens the story from “this area matters” to “this is what we still could not explain or establish before this paper.”

The gap should usually match the paper's actual scale of contribution:

- case-study paper -> case-identification / interpretation gap
- population paper -> demographic / trend / comparison gap
- theory paper -> mechanism / consistency / prediction gap

Do not ask a population-level question if the paper only provides one-object evidence, unless the poster explicitly frames the paper as an existence proof or method anchor.

### What this paper is selling

This section should be **2-3 sentences**.

It should answer:

- what is the paper trying to persuade us to believe?
- what is the strongest knowledge increment here?
- why is this paper worth sharing during a coffee break?

This is not a review report. If needed, you may include a mild caveat, but the main job is to identify the paper's strongest selling point.

### Key results to remember

Use **3-4 short bullets**.

Each bullet should be:

- evidence-centered
- concrete enough to remember
- clearly tied to the selling point
- stripped of nonessential method detail

Prefer bullets that sound like “busy-reader take-aways,” not notebook fragments.

## Story Logic: Sections Must Connect

The poster should read as one argument, not four independent summaries.

Required logical chain:

1. `Background` explains why the question matters.
2. `Knowledge gap` states what was missing before this paper.
3. `What this paper is selling` says what the paper claims to add or clarify.
4. `Key results to remember` provide the evidence or memorable consequences supporting that claim.

If the story does not flow in that order, rewrite it.

Common failure modes to avoid:

- `Background` is broad, but `Knowledge gap` is about something else.
- `Selling` is generic and does not answer the stated gap.
- `Key results` are true facts from the paper but do not support the selling point.
- The poster asks one question but answers another.
- The text sounds technically correct but not interesting.

## Figure Selection Rules

Choose figures that help a reader understand the story quickly.

Prioritize, in order:

1. a figure that defines the object, sample, or problem
2. a figure that shows the main result
3. a figure that places the result in a broader context or comparison

Usually keep **2-3 strong figures**. Use a 4th only if it clearly adds narrative value.

Avoid figures that are mainly:

- methods flowcharts
- parameter-corner plots
- internal sanity checks
- specialist diagnostics that require too much setup

unless they are the only way to make the core claim trustworthy.

## Figure Captions

Each figure caption should answer:

- why is this figure here?
- what should a busy reader remember from it?

Captions should interpret, not merely label.

Bad caption style:

- describes plot axes without telling the point
- restates the panel title only
- explains procedural details but not scientific meaning

Good caption style:

- says what the figure establishes
- says why it matters to the paper's main claim
- uses short, memorable phrasing

## Methods: Default Restraint

Do **not** spend much poster space on methods unless method trust is central to the claim.

A little method is useful only when it answers:

- why should we trust this interpretation?
- what is special about the evidence?
- what breaks a previous ambiguity?

If the method is not carrying that burden, trim it.

## Style

- Title and main text font stack: `Helvetica, Arial, sans-serif`.
- Subtitle: italic, non-bold, in the same Helvetica stack.
- Knowledge-gap / highlighted prompt can use `"Gill Sans", "Gill Sans MT", Helvetica, Arial, sans-serif`.
- Avoid long paragraphs.
- Use bold sparingly, only for the words people should actually remember.
- Figures should carry most of the information.
- The poster must fit on one common display without scrolling.
- Do not force image stretching; preserve figure aspect ratios.

## Final Self-Check Before Render

Before rendering, verify:

1. Is the poster interesting to someone who has not read the paper?
2. Does the headline communicate a real take-away?
3. Are `Background` and `Knowledge gap` tightly linked?
4. Does `What this paper is selling` clearly answer that gap?
5. Do `Key results to remember` actually support the selling point?
6. Does each figure support a specific part of the story?
7. Could a reader explain the paper's main point after 15-30 seconds?
8. Have you removed method detail that does not improve trust?
9. Do the figures carry most of the information visually?
10. Does the layout remain clean after `check`?

If any answer is no, revise `poster.html` and rerun `check`.

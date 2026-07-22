---
name: graphics-plan
description: Plan and build motion graphics for the video — lower-thirds, explainer cards, callouts, lists, stats, b-roll, and zoom emphasis — using the HyperFrames engine. Use for "do/run the graphics", "add a graphic here", "add a motion graphic/visual". Format-specific (step 3). Produces an editable plan.json, then renders and composites per-beat.
---

# Graphics (Stage 3) — format-specific

Give the cut visual life. This is the step that separates a real edit from AI slop,
so **plan intentionally**, then build. The engine is HyperFrames (HTML → video).

## 1. Scaffold the plan

```
python scripts/plan_graphics.py --job "<job>"
```
Writes `graphics/plan.json` with correctly-timed **placeholder** beats for the job's
format. Each beat is a time span + a `kind` + copy + a `preset`.

## 2. Rewrite the plan intelligently (your real job)

Open `graphics/plan.json` and the transcript, then for each beat make it *good*:
- Choose the right **kind**: `lower-third`, `top-card`, `hook-card`, `callout`,
  `list`, `quote`, `stat`, `b-roll`, `logo-bug`, `zoom`, `transition` (see
  `scripts/lib/plan.py` for the list).
- Write **tight on-screen copy** — not the full sentence. Titles are 2–6 words;
  bullets are phrases. On-screen text is a headline, not a transcript.
- Time beats to land *as the point is made* (`t_in`/`t_out` are timeline seconds).
  Don't stack overlapping cards unless intended. Aim for the density in
  `config/pipeline.json → beats_per_minute_target` (short-form is denser).
- Add **assets** (logos/screenshots/b-roll) by path in `assets`.
- Pick the **preset** per format default (long-form → `liquid-glass-style`,
  short-explainer → `signature-style`, short-tiktok → `tiktok-raw-style`) unless the
  user wants otherwise.
- Use `zoom` beats (long-form) for punch-in emphasis on key lines — no text layer.

## 3. Build

```
python scripts/build_graphics.py --job "<job>"
```
Renders each beat with HyperFrames and composites overlays (+ zooms) onto the cut →
`graphics/composited.mp4`. **Incremental**: unchanged beats are reused from cache, so
rebuilds after edits are fast.

## Format specifics

- **long-form**: full-frame glass cards, gentle ken-burns `zoom` beats, corner logo.
- **short-explainer**: cards pinned to the **top half** (face stays in the bottom half).
- **short-tiktok**: one bold **hook-card** on the opening line, then mostly raw.

## Then

Do a **second-pass** with the user (that skill), then captions (short-form) → music →
export. If graphics look wrong everywhere, check `config/brand.tokens.json` and the
preset — one change rebrands all beats.

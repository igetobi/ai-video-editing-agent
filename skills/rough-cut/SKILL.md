---
name: rough-cut
description: Transcribe raw footage and cut out silence, dead air, and filler to produce a tight rough cut. Use for "do the rough cut", "cut this down", "trim the dead space/filler", or precise cut fixes like "you cut too close to that word" / "leave that stumble out". Built on WhisperX word-level timestamps and an editable EDL.
---

# Rough cut (Stage 2)

Turn raw footage into a tight `cut/rough.mp4`. Two steps: transcribe, then cut.

## 1. Transcribe (once per job)

```
python scripts/transcribe.py --job "<job>"
```
Produces word-level `transcript/transcript.json` and `transcript/corrected.json`
(brand/spelling fixes from `presets/caption-corrections.json` applied). Word-level
timing is what makes every downstream edit precise.

## 2. Cut

```
python scripts/rough_cut.py --job "<job>"          # builds edl.json + renders rough.mp4
python scripts/rough_cut.py --job "<job>" --aggressive   # also cut like/basically/actually
```
- Silence longer than `min_gap` and hesitations (um/uh/erm) are removed automatically.
- Discourse fillers are **flagged in the EDL note**, not auto-cut (avoids mangling
  meaning). Use `--aggressive` to cut them too.
- Thresholds live in `config/pipeline.json → rough_cut`.

Report the before/after duration and how many segments were flagged. Offer to play
`cut/rough.mp4`.

## Fixing cuts (natural language → precise EDL edits)

The cut is `cut/edl.json` — a list of kept spans with source in/out and word indices.
Edit it, then **re-render without re-analyzing**: `python scripts/apply_cuts.py --job "<job>"`.

Common fixes (see `docs/PROMPTING.md` for more):
- **"you cut too close to 'Claude'"** → find the segment containing that word, lower
  its `src_in` by ~0.1–0.2s (more lead), or use `EDL.pad(seg_id, lead=0.15)`.
- **"left an extra word at the end"** → lower that segment's `src_out`, or split it.
- **"put that line back"** → add a segment spanning the raw source range you want.
- **"drop that whole take"** → delete the segment(s).

Keep the padding subtle; over-padding reintroduces the silence you removed.

## Lock it

Confirm the rough cut with the user **before graphics** — beats are timed to this
cut. Then move to **graphics-plan**.

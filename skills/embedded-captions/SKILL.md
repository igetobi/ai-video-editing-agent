---
name: embedded-captions
description: Burn animated word-level captions into short-form videos. Use for "add captions", "add subtitles", "burn in captions". Short-form only (explainer centered/locked, tiktok low under the face); long-form ships with YouTube CC. Reuses WhisperX word timings on the edited timeline — no re-transcription.
---

# Captions (Stage 5) — format-specific

Add on-beat, word-level captions. Words appear as spoken, with the active word
highlighted — the signature short-form look.

## Run

```
python scripts/captions.py --job "<job>"
python scripts/captions.py --job "<job>" --position low       # override placement
python scripts/captions.py --job "<job>" --preset tiktok-raw-style
```
- Captions follow the **edited** timeline (word timings are remapped through the EDL),
  and reuse the existing transcript — nothing is re-transcribed.
- Burns onto the current best render (`composited.mp4` if present, else `rough.mp4`)
  → `captions/captioned.mp4`.

## Format behavior

- **short-explainer** → centered, locked between the top-half graphic and the
  bottom-half face (`captions-style`, black rounded box, word rise-in).
- **short-tiktok** → low, just under the face, bold all-caps with stroke
  (`tiktok-raw-style`).
- **long-form** → captions are **disabled** by default (YouTube CC handles it). If the
  user insists, `--force`.

## Style

Look/feel lives in `presets/captions-style.json` / `tiktok-raw-style.json` and the
brand font (`config/brand.tokens.json → font.caption`; the demo uses Coolvetica —
drop the font in `assets/fonts/`). Tweak size/box/highlight there, then re-run.

## Then

Optional **background-music**, then **export**.

---
name: thumbnail-generator
description: Generate a video thumbnail — grab a hero frame and optionally overlay a punchy title in the brand font. Use for "make a thumbnail", "generate a thumbnail". Always for long-form, optional for short-explainer, skipped for tiktok-raw.
---

# Thumbnail generator

Create `thumbnail/<job>.png` from a strong frame of the edit.

## Run

```
python scripts/thumbnail.py --job "<job>" --time 3.2 --title "I automated my editing"
python scripts/thumbnail.py --job "<job>" --time 3.2          # frame only, no text
```
- `--time` is the timestamp (seconds) of the frame to grab. Pick an expressive,
  in-focus moment (open eyes, mid-gesture) — scrub the render and choose deliberately.
- `--title` overlays bold text in the brand display font (`config/brand.tokens.json →
  font.display_url`, e.g. Coolvetica) on an accent box.

## Guidance by format

- **long-form** → always make one. Big, legible title; face clearly visible.
- **short-explainer** → optional; usually the cover frame is enough.
- **short-tiktok** → skip.

Grabs from the most advanced render available, so run it after graphics/captions for
the best-looking frame.

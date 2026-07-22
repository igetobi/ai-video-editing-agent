# Formats

A format is a delivery target. Choosing one at intake sets dimensions and decides how
**steps 3 (graphics)** and **5 (captions)** behave — the other five stages are
identical across formats. Definitions live in `config/formats.json`.

## long-form — YouTube

- **16:9, 1920×1080, 30fps.**
- **Graphics:** `liquid-glass-style` — frosted panels, gentle parallax, ken-burns
  `zoom` beats for emphasis. Full-frame. Corner logo bug.
- **Captions:** off (ship with YouTube CC). `captions.py --force` to override.
- **Thumbnail:** always.

This is the demo intro look — cinematic, sparse, high-production.

## short-explainer — vertical explainer

- **9:16, 1080×1920, 30fps.**
- **Graphics:** `signature-style` — clean cards pinned to the **top half**; your face
  stays in the **bottom half**.
- **Captions:** `captions-style` — **centered, locked** between the top-half graphic
  and the bottom-half face. Black rounded box, words rise in on-beat.
- **Thumbnail:** optional.

## short-tiktok — raw / punchy

- **9:16, 1080×1920, 30fps.**
- **Graphics:** `tiktok-raw-style` — one bold **hook card** on the opening line, then
  mostly raw footage.
- **Captions:** low, just under the face; bold all-caps with a stroke.
- **Thumbnail:** skipped.

## Reframing

Short formats set `reframe: true`. If your source is 16:9, the pipeline fits it into
9:16 (see `ffmpeg.scale_pad`); shoot vertical when you can for best quality.

## Add your own format

Add an entry to `config/formats.json`:

```jsonc
"my-format": {
  "label": "…", "aspect": "9:16", "width": 1080, "height": 1920, "fps": 30,
  "graphics": { "default_preset": "signature-style", "layout": "top-half" },
  "captions": { "enabled": true, "preset": "captions-style", "position": "center" },
  "thumbnail": "optional", "reframe": true
}
```

Then `intake.py --format my-format`. If you want a new look, add a preset in
`presets/` (copy an existing one) and reference brand tokens with `{{token.path}}`.

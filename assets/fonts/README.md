# Fonts

Drop your display/caption font here (`.otf` or `.ttf`) and point
`config/brand.tokens.json → font.display_url` / `font.caption_url` at it.

The demo look uses **Coolvetica** (`Coolvetica.otf`) — a great, punchy caption font.
Any bold display face works. If this folder is empty, ffmpeg/HyperFrames fall back to
the system font named in the token (e.g. `Arial Black`), so captions still render.

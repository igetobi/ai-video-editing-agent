"""Turn a graphics-plan Beat into a HyperFrames composition (an HTML file).

Matches the real HyperFrames composition contract (verified against
`hyperframes init`):
  * a root element with `data-composition-id`, `data-start`, `data-duration`,
    `data-width`, `data-height`;
  * renderable elements carry `class="clip"` + `data-start`/`data-duration`;
  * animation is a **paused GSAP timeline** registered on
    `window.__timelines[<composition-id>]`, which HyperFrames scrubs frame-by-frame
    ("seek, don't play"). This is why we drive opacity/transform through GSAP rather
    than CSS keyframes — CSS animation playback state is not deterministically
    seekable, GSAP timelines are.

Compositions render on a transparent background so each beat is an alpha overlay
(rendered as MOV/WebM) that composites over the footage at its timeline position.
'zoom'/'transition' beats are camera-only and produce no overlay.
"""

from __future__ import annotations

from typing import Any

from scripts.lib.plan import Beat

GSAP_CDN = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pos_css(position: str, safe: dict[str, float]) -> str:
    top = safe.get("top", 0.06) * 100
    bottom = safe.get("bottom", 0.10) * 100
    left = safe.get("left", 0.06) * 100
    right = safe.get("right", 0.06) * 100
    mapping = {
        "top": f"top:{top}%;left:{left}%;right:{right}%;",
        "bottom": f"bottom:{bottom}%;left:{left}%;right:{right}%;",
        "center": "top:50%;left:50%;transform:translate(-50%,-50%);",
        "tl": f"top:{top}%;left:{left}%;",
        "tr": f"top:{top}%;right:{right}%;",
        "bl": f"bottom:{bottom}%;left:{left}%;",
        "br": f"bottom:{bottom}%;right:{right}%;",
        "auto": f"bottom:{bottom}%;left:{left}%;right:{right}%;",
    }
    return mapping.get(position, mapping["auto"])


def _card_css(preset: dict[str, Any]) -> str:
    card = preset.get("card", {})
    typ = preset.get("type", {})
    blur = card.get("backdrop_blur")
    backdrop = f"backdrop-filter:blur({blur}px);-webkit-backdrop-filter:blur({blur}px);" if blur else ""
    scale = float((preset.get("_beat_params") or {}).get("scale", 1.0))
    return f"""
    #card {{
      position:absolute; transform-origin:center;
      background:{card.get('bg', 'rgba(21,21,28,0.9)')};
      border:{card.get('border', '1px solid rgba(255,255,255,0.1)')};
      border-radius:{card.get('radius', 24)}px;
      box-shadow:{card.get('shadow', '0 20px 60px rgba(0,0,0,0.45)')};
      padding:{card.get('padding', 40)}px; {backdrop}
      color:{typ.get('title_color', '#fff')};
      zoom:{scale};
    }}
    .accent-bar {{ position:absolute; left:0; top:24px; bottom:24px; width:6px; border-radius:6px;
                   background:{card.get('accent', '#E07A3F')}; }}
    .title {{ font-family:{typ.get('title_font', 'sans-serif')}; font-size:{typ.get('title_size', 64)}px;
              font-weight:800; line-height:1.05; margin:0; }}
    .subtitle {{ font-family:{typ.get('body_font', 'sans-serif')}; font-size:{typ.get('body_size', 40)}px;
                 color:{typ.get('body_color', '#A0A0AE')}; margin:12px 0 0; }}
    ul.body {{ list-style:none; padding:0; margin:18px 0 0; }}
    ul.body li {{ font-family:{typ.get('body_font', 'sans-serif')}; font-size:{typ.get('body_size', 40)}px;
                  color:{typ.get('body_color', '#cfd0da')}; margin:0 0 14px; padding-left:34px; position:relative; }}
    ul.body li::before {{ content:''; position:absolute; left:0; top:0.55em; width:14px; height:14px;
                          border-radius:4px; background:{card.get('accent', '#E07A3F')}; }}
    """


def _inner_html(beat: Beat, preset: dict[str, Any]) -> str:
    parts = ['<div class="accent-bar"></div>'] if preset.get("card", {}).get("accent") else []
    if beat.title:
        parts.append(f'<h1 class="title">{_esc(beat.title)}</h1>')
    if beat.subtitle:
        parts.append(f'<p class="subtitle">{_esc(beat.subtitle)}</p>')
    if beat.body:
        parts.append('<ul class="body">' + "".join(f"<li>{_esc(b)}</li>" for b in beat.body) + "</ul>")
    return "".join(parts)


def build_composition(beat: Beat, preset: dict[str, Any], width: int, height: int, fps: float) -> str:
    dur = round(max(0.1, beat.duration), 3)
    layout_pos = beat.position if beat.position != "auto" else preset.get("layout_pos", "auto")
    pos = _pos_css(layout_pos, preset.get("safe_area", {}))
    preset = {**preset, "_beat_params": beat.params}

    if beat.kind in ("b-roll", "logo-bug") and beat.assets:
        media = beat.assets[0]
        box = "width:44%;" if beat.kind == "logo-bug" else "width:70%;"
        card = (
            f'<div id="card" class="clip" data-start="0" data-duration="{dur}" data-track-index="1" '
            f'style="{pos}{box}">'
            f'<img src="{_esc(media)}" style="width:100%;height:auto;display:block;border-radius:18px;'
            f'box-shadow:0 18px 50px rgba(0,0,0,0.5);"/></div>'
        )
    else:
        card = (
            f'<div id="card" class="clip" data-start="0" data-duration="{dur}" data-track-index="1" '
            f'style="{pos}max-width:82%;">{_inner_html(beat, preset)}</div>'
        )

    in_dur = float(preset.get("animation", {}).get("enter_dur", 0.45))
    out_dur = float(preset.get("animation", {}).get("exit_dur", 0.3))
    out_at = max(0.01, dur - out_dur)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width={width}, height={height}"/>
<script src="{GSAP_CDN}"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:{width}px;height:{height}px;overflow:hidden;background:transparent;}}
body{{font-family:{preset.get('type', {}).get('body_font', 'Inter, sans-serif')};}}
{_card_css(preset)}
</style>
</head>
<body>
  <div id="root"
       data-composition-id="{beat.id}"
       data-start="0" data-duration="{dur}"
       data-width="{width}" data-height="{height}" data-fps="{fps}"
       data-background="transparent">
    {card}
  </div>
  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
    tl.from("#card", {{ opacity: 0, y: 28, scale: 0.98, duration: {in_dur}, ease: "power3.out" }}, 0);
    tl.to("#card", {{ opacity: 0, duration: {out_dur}, ease: "power2.in" }}, {out_at});
    window.__timelines["{beat.id}"] = tl;
  </script>
</body>
</html>
"""

"""Turn a graphics-plan Beat into a HyperFrames composition (an HTML file).

HyperFrames renders plain HTML with ``data-*`` timing attributes to deterministic
video. We generate that HTML from the beat's structured fields and the resolved
style preset (brand tokens already expanded). Animations use CSS keyframes with
fixed durations and ``animation-fill-mode: both`` so they are seek-safe (the whole
point of HyperFrames: seek, don't play).

Compositions render on a transparent background so each beat is an alpha overlay
that composites over the footage at its timeline position (see composite step).
Only 'zoom'/'transition' kinds are camera-only and produce no overlay.
"""

from __future__ import annotations

from typing import Any

from scripts.lib.plan import Beat


def _pos_css(position: str, safe: dict[str, float]) -> str:
    top = safe.get("top", 0.06) * 100
    bottom = safe.get("bottom", 0.10) * 100
    left = safe.get("left", 0.06) * 100
    right = safe.get("right", 0.06) * 100
    mapping = {
        "top": f"top:{top}%;left:{left}%;right:{right}%;",
        "bottom": f"bottom:{bottom}%;left:{left}%;right:{right}%;",
        "center": f"top:50%;left:50%;transform:translate(-50%,-50%);",
        "tl": f"top:{top}%;left:{left}%;",
        "tr": f"top:{top}%;right:{right}%;",
        "bl": f"bottom:{bottom}%;left:{left}%;",
        "br": f"bottom:{bottom}%;right:{right}%;",
        "auto": f"bottom:{bottom}%;left:{left}%;right:{right}%;",
    }
    return mapping.get(position, mapping["auto"])


def _keyframes(preset: dict[str, Any]) -> str:
    anim = preset.get("animation", {})
    in_dur = float(anim.get("enter_dur", 0.45))
    out_dur = float(anim.get("exit_dur", 0.3))
    return f"""
    @keyframes enter {{ from {{ opacity:0; transform: translateY(28px) scale(0.98); }}
                        to   {{ opacity:1; transform: translateY(0) scale(1); }} }}
    @keyframes exit  {{ from {{ opacity:1; }} to {{ opacity:0; }} }}
    @keyframes sheen {{ 0%{{background-position:-150% 0}} 100%{{background-position:250% 0}} }}
    .enter {{ animation: enter {in_dur}s var(--ease-in) both; }}
    .exit  {{ animation: exit {out_dur}s ease both; }}
    """


def _card_css(preset: dict[str, Any]) -> str:
    card = preset.get("card", {})
    typ = preset.get("type", {})
    blur = card.get("backdrop_blur")
    backdrop = f"backdrop-filter: blur({blur}px); -webkit-backdrop-filter: blur({blur}px);" if blur else ""
    return f"""
    .card {{
      position:absolute;
      background:{card.get('bg', 'rgba(21,21,28,0.9)')};
      border:{card.get('border', '1px solid rgba(255,255,255,0.1)')};
      border-radius:{card.get('radius', 24)}px;
      box-shadow:{card.get('shadow', '0 20px 60px rgba(0,0,0,0.45)')};
      padding:{card.get('padding', 40)}px;
      {backdrop}
      color:{typ.get('title_color', '#fff')};
    }}
    .accent-bar {{ position:absolute; left:0; top:24px; bottom:24px; width:6px;
                   border-radius:6px; background:{card.get('accent', '#E07A3F')}; }}
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
        items = "".join(f"<li>{_esc(b)}</li>" for b in beat.body)
        parts.append(f'<ul class="body">{items}</ul>')
    return "".join(parts)


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def build_composition(beat: Beat, preset: dict[str, Any], width: int, height: int, fps: float) -> str:
    """Return HTML for one beat's HyperFrames composition."""
    safe = preset.get("safe_area", {})
    motion = {
        "in": "cubic-bezier(0.16,1,0.3,1)",
        "out": "cubic-bezier(0.7,0,0.84,0)",
    }
    pos = _pos_css(beat.position if beat.position != "auto" else preset.get("layout_pos", "auto"), safe)

    # b-roll / logo kinds render an image element instead of a text card.
    if beat.kind in ("b-roll", "logo-bug") and beat.assets:
        media = beat.assets[0]
        box_style = "width:44%;" if beat.kind == "logo-bug" else "width:70%;"
        inner = (
            f'<div class="media enter exit" style="position:absolute;{pos}{box_style}">'
            f'<img src="{_esc(media)}" style="width:100%;height:auto;display:block;'
            f'border-radius:{preset.get("card", {}).get("radius", 18)}px;'
            f'box-shadow:0 18px 50px rgba(0,0,0,0.5);"/></div>'
        )
    else:
        card_pos = pos
        inner = (
            f'<div class="card enter exit" style="{card_pos}max-width:82%;">'
            f'{_inner_html(beat, preset)}</div>'
        )

    css = f"""
    :root {{ --ease-in:{motion['in']}; --ease-out:{motion['out']}; }}
    * {{ box-sizing:border-box; }}
    html,body {{ margin:0; padding:0; background:transparent; }}
    #stage {{ position:relative; width:{width}px; height:{height}px; overflow:hidden;
              font-family:{preset.get('type', {}).get('body_font', 'sans-serif')}; }}
    {_card_css(preset)}
    {_keyframes(preset)}
    """

    dur = round(beat.duration, 3)
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<style>{css}</style>
</head>
<body>
  <div id="stage"
       data-composition-id="{beat.id}"
       data-width="{width}" data-height="{height}"
       data-fps="{fps}" data-duration="{dur}"
       data-start="0" data-background="transparent">
    <div class="clip" data-start="0" data-duration="{dur}" data-track-index="0">
      {inner}
    </div>
  </div>
</body>
</html>
"""

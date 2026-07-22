---
name: second-pass
description: Iterate on individual graphics with the user — move, recolor, resize, restyle, retime, swap assets, change a beat's kind. Use for per-graphic tweaks like "move this to the bottom", "make it the accent color", "add the logo PNG", "make it smaller", "start the zoom earlier". Fast because only the changed beat re-renders.
---

# Second pass (Stage 4)

The refinement loop that makes graphics *dialed in*. The user reacts to a beat, you
edit that beat in `graphics/plan.json`, and rebuild **only that beat**:

```
python scripts/build_graphics.py --job "<job>" --only b003
```
The content-hash cache means one beat re-renders in seconds, not the whole video.
Re-composite is automatic. Show the result and keep going.

## Editing a beat (in graphics/plan.json)

- **Move** → `position`: `top | bottom | center | tl | tr | bl | br` (or tune
  `params` offsets). "It's covering my face / on my forehead" → `bottom`.
- **Recolor** → set an accent in the beat's `params`, or (to change it everywhere)
  edit `config/brand.tokens.json → color.accent`.
- **Resize** → `params.scale` (e.g. `0.85` for smaller).
- **Retime** → `t_in` / `t_out`. "Start the zoom earlier" → lower `t_in`.
- **Swap kind** → e.g. `list` → `stat`, or `lower-third` → `callout`.
- **Add an asset/PNG/logo** → add its path to `assets` (drop the file in `assets/`).
  "Add the bouncing/glowing mascot" → set `kind` appropriately and reference
  `{{mascot.image}}` (from brand tokens) or a direct path in `assets`.
- **Disable** a beat without deleting → `"enabled": false`.

Full phrase→edit mapping is in `docs/PROMPTING.md`.

## Working style

- Change **one thing at a time** unless the user lists several — batching several
  edits into one rebuild is fine and faster (`--only b003 b004 b005`).
- After each rebuild, state exactly what changed and roughly how long the render was.
- If the user is happy with everything, move on: captions (short-form) → music →
  export.

## Guardrail

Don't silently re-cut the video here — beats are timed to the locked rough cut. If
the user wants a content change (add/remove spoken lines), flag that it means editing
the EDL and re-timing affected beats.

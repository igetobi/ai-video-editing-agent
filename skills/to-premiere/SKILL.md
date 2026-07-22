---
name: to-premiere
description: Export the agent's cut to Premiere Pro / DaVinci Resolve / Final Cut to finish by hand. Use for "hand this off to Premiere", "give me an EDL/XML", "I want to finish this manually". Writes CMX3600 EDL and FCPXML that carry the cut decisions; relink to the raw clip in the NLE.
---

# To Premiere (off-ramp)

The escape hatch: rough-cut in the agent, finish in a traditional editor. Available
any time after the rough cut (stage 2) exists.

## Run

```
python scripts/to_premiere.py --job "<job>"
```
Writes:
- `premiere/<job>.edl` — **CMX3600**, imports into Premiere, Resolve, Avid, FCP.
- `premiere/<job>.fcpxml` — richer, keeps the clip name.

## In the NLE

1. Import the `.edl` or `.fcpxml`.
2. When prompted, **relink media** to the raw clip in `projects/<job>/raw/`.
3. You'll get the agent's exact cut as a timeline of clips, ready to polish.

Use this when a client needs the project file, or when a specific effect is easier by
hand. The agent's JSON (`edl.json`) and the NLE export stay in sync — re-export after
any cut change.

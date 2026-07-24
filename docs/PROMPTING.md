# Natural-language editing cheatsheet

You edit by talking. Claude translates each request into a precise edit of `edl.json`
(the cut) or `plan.json` (the graphics), then re-renders. This maps common phrases to
what actually changes.

## Cutting (edits `cut/edl.json`, then `apply_cuts.py`)

| You say | What happens |
|---------|--------------|
| "trim the dead space / silences" | already done by the rough cut; tighten via `min_gap` in `pipeline.json` |
| "cut the filler too" | re-run `rough_cut.py --aggressive` (cuts like/basically/actually) |
| "you cut a little too close to 'Claude'" | find that segment, lower its `src_in` ~0.1–0.2s (more lead) |
| "there's an extra word at the end of that line" | lower that segment's `src_out`, or split it |
| "leave that stumble/retake out" | add it to `cut/excludes.json` (phrase, `from→to`, or time range) and re-run rough-cut — reversible |
| "cut every time I said 'let me restart'" | add each as an excludes entry; re-run |
| "put that sentence back in" | remove it from excludes / add a segment spanning the raw range |
| "make the cuts smoother / harder" | smooth cross-dissolves are on by default; `rough_cut.py --hard-cuts` for hard cuts (tune `render.transition_sec`) |
| "the audio is uneven" | it's loudness-normalized; adjust `audio_target_lufs` if needed |

After any cut change, re-render: `python scripts/apply_cuts.py` (—`--job` defaults to
your newest project). If graphics already exist, retime affected beats (`t_in`/`t_out`).

## Graphics (edits `graphics/plan.json`, then `build_graphics.py --only <ids>`)

| You say | What happens |
|---------|--------------|
| "move it to the bottom" / "it's covering my face" | beat `position: "bottom"` |
| "put it in the top-right corner" | `position: "tr"` |
| "make it smaller" | `params.scale: 0.85` |
| "make it the accent / orange color" | set an accent in `params`, or change `color.accent` in brand tokens to reskin all |
| "start the zoom earlier" | lower the zoom beat's `t_in` |
| "hold it a bit longer" | raise `t_out` |
| "add the logo / that PNG / the mascot" | add the path to the beat's `assets` (drop file in `assets/`) |
| "make this a bulleted list instead" | `kind: "list"`, fill `body: [...]` |
| "turn this into a big stat" | `kind: "stat"`, put the number in `title` |
| "tighten the copy" | shorten `title`/`body` — on-screen text is a headline, not the transcript |
| "remove this graphic" | `enabled: false` (keeps it for later) or delete the beat |
| "change everything to the glass style" | set each beat's `preset`, or change the format default |

Rebuild only what changed: `python scripts/build_graphics.py --job "<job>" --only b003 b004`.
One beat re-renders in seconds.

## Captions (short-form)

| You say | What happens |
|---------|--------------|
| "add captions" | `captions.py` (uses the format's caption preset) |
| "put them lower / higher / centered" | `--position low|center|top` (or a 0–1 fraction) |
| "make them bigger / change the font / box" | edit `presets/captions-style.json` (or `tiktok-raw-style.json`) |
| "highlight the word being said" | `highlight_mode: "active-word"` (default); `"none"` for static |

## Music

| You say | What happens |
|---------|--------------|
| "add this song under it" | `background_music.py --music <path>` |
| "make the music quieter / louder" | `--gain -26` (quieter) / `--gain -18` (louder) |

## Export

| You say | What happens |
|---------|--------------|
| "export it / ship it / we're done" | `export.py` → `outputs/<job>.final.mp4` + Downloads |
| "hand this to Premiere" | `to_premiere.py` → EDL + FCPXML |
| "clean up the big render files" | `prune.sh "<job>"` (keeps sources + final) |

## Principle

If a change can't be expressed as an edit to `edl.json`, `plan.json`, a preset, or the
brand tokens, it probably shouldn't be done here — that's the sign to use the
`to-premiere` off-ramp and finish by hand.

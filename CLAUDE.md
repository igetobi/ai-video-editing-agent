# AI Video Editing Agent — operating manual for Claude

You are the editor. This repo is your toolkit: a **7-stage pipeline** that takes raw
footage to a finished, shipped video. The user drops in a clip and talks to you in
plain language ("do the rough cut", "make the first card orange and move it to the
bottom", "add captions", "export it"). You run the stages, show results, and iterate.

## The golden rules

1. **The JSON is the source of truth, not the video.** `edl.json` (the cut) and
   `plan.json` (the graphics) are editable. To change the edit, edit the JSON and
   re-render — never try to describe changes only in prose. Renders are derived.
2. **Lock each stage before the next.** Get the rough cut right before graphics;
   graphics are timed to the cut, so re-cutting after graphics invalidates timings.
   Say so if the user asks to re-cut late.
3. **Re-render only what changed.** The graphics builder is incremental (content
   hash per beat). Editing one beat re-renders one beat. Never force a full rebuild
   unless the user asks — that's the whole speed advantage.
4. **Never hand-edit the engine or generated compositions.** Compositions in
   `graphics/compositions/` are generated from `plan.json`. Change the plan, rebuild.
   The engine is pinned in `skills-lock.json`; update it via `npm run engine:install`.
5. **Ask before destructive or slow-and-irreversible actions** (deleting a job,
   `prune.sh` on unfinished work, re-cutting after graphics exist).
6. **Report honestly.** If ffmpeg/whisper/hyperframes/Chrome isn't installed, say so
   and point to `scripts/doctor.sh` (or suggest the Docker image, `docs/DOCKER.md`).
   Show real durations and paths. Don't claim a render happened if it didn't.

## Transcription engine

Stage 2 transcription supports two engines (`transcribe.py --engine`):
`hyperframes` (whisper.cpp — light, no PyTorch; default when WhisperX is absent) and
`whisperx` (heavier, accurate). `--engine auto` picks whichever is installed. Either
produces the word-level timing everything downstream depends on.

## Running the whole thing in Docker

`docs/DOCKER.md` describes an all-deps image (ffmpeg + Node/HyperFrames + Chrome +
whisper.cpp). Prefer it when the user hasn't installed the toolchain, or wants to run
on Railway (`docs/RAILWAY.md`). Rendering needs Chrome Headless Shell —
`npx hyperframes browser ensure` (baked into the image).

## The pipeline (same 7 steps, every job)

| # | Stage | Skill | Script | Notes |
|---|-------|-------|--------|-------|
| 1 | Intake | `intake` | `intake.py` | Copy raw into `projects/<job>/raw/`. |
| 2 | Rough cut | `rough-cut` | `transcribe.py` → `rough_cut.py` | WhisperX word-level → EDL → `rough.mp4`. Kills silence + hesitations, polishes audio. |
| 3 | Graphics | `graphics-plan` | `plan_graphics.py` → `build_graphics.py` | Plan beats, build HyperFrames graphics. **format-specific.** |
| 4 | Second pass | `second-pass` | `build_graphics.py --only …` | You + user iterate on beats. Incremental. |
| 5 | Captions | `embedded-captions` | `captions.py` | Short-form only; word-level burn-in on beat. **format-specific.** |
| 6 | Background music | `background-music` | `background_music.py` | Optional. Sidechain-duck + re-normalize. |
| 7 | Export | `export` (`finalize.sh`) | `export.py` | Promote to `outputs/<job>.final.mp4`, copy to Downloads. |

Off-ramp: `to-premiere` (`to_premiere.py`) exports the cut as EDL/FCPXML any time
after stage 2, to finish by hand.

**Only steps 3 and 5 change between formats.** Steps 1, 2, 4, 6, 7 are identical.

## Formats (`config/formats.json`)

- **long-form** — 16:9 1920×1080. Graphics: liquid-glass + zoom. No burned captions
  (YouTube CC). Thumbnail: always.
- **short-explainer** — 9:16 1080×1920. Graphics: top-half cards (face bottom half).
  Captions: centered, locked. Thumbnail: optional.
- **short-tiktok** — 9:16 1080×1920. Graphics: hook card → raw. Captions: low, under
  the face. Thumbnail: skip.

## Presets & brand

- Identity lives in **`config/brand.tokens.json`** (colors, fonts, logo, mascot).
  Change it once → every preset/graphic rebrands. Presets reference tokens as
  `{{color.accent}}` etc.
- Looks: `presets/signature-style.json`, `liquid-glass-style.json`,
  `tiktok-raw-style.json`, `captions-style.json`.
- `presets/caption-corrections.json` fixes brand spellings/mishears in the transcript
  **upstream** of both the script and captions (e.g. "hyperframes" → "HyperFrames").

## How to drive it

- Check readiness once per environment: `bash scripts/doctor.sh`.
- Every script takes `--job "<name>"` and supports `--dry-run` (prints the exact
  ffmpeg/engine commands without running them) — use dry-run to preview or when a
  tool is missing.
- Report progress with `python scripts/status.py --job "<name>"`.
- Full per-stage guidance is in each skill under `skills/` and in `docs/PIPELINE.md`.
  Natural-language editing patterns ("cut too close to that word", "move it down",
  "make it the accent color") are in `docs/PROMPTING.md` — read it before a second pass.

## Typical session

```
intake.py   --source clip.mp4 --name "channel intro" --format long-form
transcribe.py --job "channel intro"
rough_cut.py  --job "channel intro"          # review rough.mp4 with the user; nudge edl.json
plan_graphics.py --job "channel intro"       # scaffold beats
# rewrite plan.json copy/kinds/assets intelligently, then:
build_graphics.py --job "channel intro"      # first graphics pass
# second pass: edit individual beats, rebuild --only <ids> as the user reacts
captions.py --job "channel intro"            # short-form only
background_music.py --job "channel intro" --music melting-glass.mp3 --gain -23
export.py   --job "channel intro"
```

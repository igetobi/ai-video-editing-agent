# AI Video Editing Agent

**Drop in raw footage. Talk to Claude. Get a finished video.**

This is a Claude Code project that edits video end-to-end: it transcribes your
footage, cuts the silence and filler, plans and builds motion graphics, adds
word-level captions, mixes background music, and exports a shipped file — all driven
by plain-language conversation. It's built on the open-source
[HyperFrames](https://github.com/heygen-com/hyperframes) HTML video engine and
WhisperX word-level transcription.

> Same 7 steps, every job, raw → done. Only two of them change per format.

```
1 Intake ──► 2 Rough cut ──► 3 Graphics ──► 4 Second pass ──► 5 Captions ──► 6 Music ──► 7 Export
             (WhisperX +      (HyperFrames,   (you + Claude,     (short-form,   (optional)   (ship +
              editable EDL)    per format)     incremental)       per format)               prune)
                    │
                    └─► off-ramp: to-premiere (EDL / FCPXML)
```

## What makes this one good

- **The edit is data, not a black box.** The cut lives in `edl.json` and the graphics
  in `plan.json` — human- and agent-readable JSON. Change the JSON, re-render. Every
  edit is precise and reversible.
- **Word-level precision.** WhisperX word timestamps mean "you cut a hair too close to
  that word" is an exact operation, not a guess.
- **Incremental re-rendering.** Each graphic beat has a content hash; editing one card
  re-renders **one card**, not the whole video. The second-pass loop is fast.
- **Conservative by default.** It removes silence and clear hesitations (um/uh) but
  *flags* discourse fillers (like/basically) for review instead of mangling your
  meaning. Opt into aggressive cutting when you want it.
- **Rebrand in one file.** Colors, fonts, logo, and mascot live in
  `config/brand.tokens.json`. Change it once, everything re-skins.
- **A real off-ramp.** Export a CMX3600 EDL / FCPXML to finish in Premiere, Resolve,
  or Final Cut whenever you want.
- **Honest & safe.** No fake renders, no auto-posting to social platforms. It stops at
  a finished file on disk and tells you the truth about what ran.

## Quickstart

```bash
# 0. One-time: install the engine + tools (see docs/SETUP.md)
npm install                       # HyperFrames
npm run engine:install            # HyperFrames agent skills
pipx install whisperx             # transcription  (or: pip install whisperx)
brew install ffmpeg               # macOS; see SETUP.md for Linux/Windows
bash scripts/doctor.sh            # verify everything

# 1. Then just talk to Claude Code in this folder:
#    "start a new long-form project for ~/Movies/intro.mov and do the rough cut"
#    "run the graphics"
#    "move the first card to the bottom and make it the accent color"
#    "add captions"
#    "add this song as background music at -23 dB: ~/Music/bed.mp3"
#    "export it"
```

Prefer buttons to prose? The same stages run from the CLI:

```bash
python scripts/intake.py --source ~/Movies/intro.mov --name "channel intro" --format long-form
python scripts/transcribe.py --job "channel intro"
python scripts/rough_cut.py  --job "channel intro"
python scripts/plan_graphics.py --job "channel intro"   # then refine plan.json
python scripts/build_graphics.py --job "channel intro"
python scripts/captions.py   --job "channel intro"      # short-form only
python scripts/background_music.py --job "channel intro" --music ~/Music/bed.mp3 --gain -23
python scripts/export.py     --job "channel intro"
```

Every script accepts `--dry-run` to print the exact ffmpeg/engine commands without
running them.

## Formats (only steps 3 & 5 differ)

| Format | Aspect | Graphics | Captions | Thumb |
|--------|--------|----------|----------|-------|
| `long-form` | 16:9 1920×1080 | liquid-glass + zoom | none (YouTube CC) | always |
| `short-explainer` | 9:16 1080×1920 | top-half cards | centered, locked | optional |
| `short-tiktok` | 9:16 1080×1920 | hook card → raw | low, under face | skip |

## Layout

```
config/      brand.tokens.json · formats.json · pipeline.json   (all the knobs)
presets/     signature · liquid-glass · tiktok-raw · captions · caption-corrections
skills/      the 9 Claude skills (intake, rough-cut, graphics-plan, second-pass, …)
scripts/     stage CLIs + lib/ (the data contracts: project, transcript, edl, plan, …)
engine/      HyperFrames adapter + composition builder (generated, never hand-edited)
projects/    one self-contained folder per job (raw, transcript, cut, graphics, …)
docs/        SETUP · PIPELINE · FORMATS · PROMPTING · ARCHITECTURE
tests/       unit tests for the pure logic (cutting, captions, edl export, planning)
```

## Docs

- **[docs/SETUP.md](docs/SETUP.md)** — install WhisperX, FFmpeg, Node/HyperFrames.
- **[docs/PIPELINE.md](docs/PIPELINE.md)** — every stage in depth.
- **[docs/FORMATS.md](docs/FORMATS.md)** — the three formats and how to add one.
- **[docs/PROMPTING.md](docs/PROMPTING.md)** — natural-language editing cheatsheet.
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — the data contracts & why.

## Requirements

Python 3.10+, Node 22+, FFmpeg, WhisperX. See `docs/SETUP.md`. Run `bash
scripts/doctor.sh` to check.

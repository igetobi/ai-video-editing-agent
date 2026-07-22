# Architecture

The design goal: make the edit **inspectable, editable, and cheap to iterate** — so an
agent can edit video precisely with natural language, and a human can always open the
hood.

## Everything is a data contract

Each stage reads and writes plain JSON. The rendered video is always *derived* from
these; it is never the source of truth.

```
raw clip
   │  transcribe.py (WhisperX)
   ▼
transcript.json ──corrections──► corrected.json          (scripts/lib/transcript.py)
   │  cutting.build_edl()
   ▼
edl.json  (kept source spans + word indices)             (scripts/lib/edl.py)
   │  apply_cuts.py (ffmpeg)
   ▼
cut/rough.mp4
   │  planning.build_plan()  +  the graphics-plan skill
   ▼
plan.json  (beats: span + kind + copy + preset)          (scripts/lib/plan.py)
   │  build_graphics.py → engine/composition.py → HyperFrames
   ▼
graphics/segments/*.mov  ──composite (ffmpeg)──► composited.mp4
   │  captions.py (ASS)          music (ffmpeg)
   ▼                                 ▼
captioned.mp4 ───────────────► scored.mp4 ──► outputs/<job>.final.mp4
```

## Why these choices

- **EDL with word indices** (`edl.py`). The cut is a list of source spans, each
  tagged with the transcript word range it came from. That's what turns "give that
  word more room" into a deterministic `src_in -= 0.15` instead of a guess.
- **Beats with a content hash** (`plan.py` + `cache.py`). Each graphic's `input_hash`
  covers its fields *and* the resolved preset fingerprint. `build_graphics.py`
  re-renders a beat only when its hash changes → editing one card re-renders one card.
  This is the incremental-render feature; it lives in `scripts/lib/cache.py`.
- **Brand tokens + `{{token}}` expansion** (`presets.py`). Presets are templates;
  identity is one file (`config/brand.tokens.json`). Changing a token changes the
  preset fingerprint, which correctly invalidates the render cache.
- **ASS for captions, HyperFrames for graphics.** Captions are pure timing over the
  transcript, so an ASS track burned in one ffmpeg pass is faster and more precise than
  a per-frame render. Graphics are design, so they go through HyperFrames (HTML →
  video), which is where LLMs are strongest.
- **ffmpeg wrappers build command *lists*** (`ffmpeg.py`) with a `--dry-run` that
  prints them. The media logic is auditable and unit-testable without ffmpeg present.

## The engine boundary

`engine/composition.py` generates HyperFrames-native HTML from a beat.
`engine/hyperframes_adapter.py` shells out to render it; the exact CLI is isolated in
`engine/engine.json` — the one place to adjust per HyperFrames version. Generated
compositions are disposable; the plan is the truth. The engine + skills are pinned in
`skills-lock.json` and updated via `npm run engine:install`, never hand-edited.

## Job isolation

Everything for a job lives under `projects/<job>/` (see `project.py`). A job is
self-contained — zip it, move it, archive it — and `job.json` tracks per-stage status
so `status.py` (and Claude) always knows where a job stands.

## Testing

Pure logic (cutting, caption ASS, EDL/FCPXML export, planning, hashing, corrections,
composition) is covered by `tests/` and runs with no external tools:
`python3 -m unittest discover -s tests -t .`. Media steps are validated via
`--dry-run` command inspection.

## Non-goals / safety

- No auto-posting to social platforms. The pipeline stops at a file on disk.
- No hand-editing of engine internals or generated compositions.
- Renders are never faked; if a tool is missing, the script says so and points to
  `scripts/doctor.sh`.

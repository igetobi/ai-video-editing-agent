"""Shared library for the AI video editing agent pipeline.

Every stage of the pipeline (intake -> rough-cut -> graphics -> second-pass ->
captions -> music -> export) reads and writes plain-JSON data contracts defined
here. The contracts are deliberately human- and agent-readable so that Claude can
make precise, natural-language edits ("give this word more room", "start the zoom
earlier") by editing structured data instead of re-deriving everything.

Modules:
    project     Job layout + job.json manifest (the source of truth for a job).
    transcript  WhisperX word-level transcript model + brand/spelling corrections.
    edl         The cut-list / EDL: which spans of the raw clip survive, in order.
    plan        The graphics plan: one "beat" per visual, with an input hash.
    ffmpeg      Thin, inspectable ffmpeg/ffprobe wrappers with --dry-run support.
    cache       Content-hash render cache that powers incremental re-rendering.
    presets     Loader for brand tokens, format presets, and style presets.
"""

__all__ = [
    "project",
    "transcript",
    "edl",
    "plan",
    "ffmpeg",
    "cache",
    "presets",
]

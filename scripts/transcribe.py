#!/usr/bin/env python3
"""Stage 2a — Transcribe to word-level timestamps.

    python scripts/transcribe.py --job "channel intro" [--engine auto|hyperframes|whisperx]

Two engines:
  * hyperframes — HyperFrames' bundled ASR (whisper.cpp / Parakeet). Light, no
    PyTorch. Needs a whisper.cpp binary on PATH (macOS: `brew install whisper-cpp`).
  * whisperx    — WhisperX (accurate, heavier: pulls in PyTorch).
`auto` prefers whisperx if it's installed, else hyperframes.

Produces:
    transcript/transcript.json   normalized word-level transcript
    transcript/corrected.json    same, with caption-corrections applied

Word-level timestamps are what make precise cutting and on-beat captions possible.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import hyperframes_adapter as hfa  # noqa: E402
from scripts.lib import ffmpeg, presets, project  # noqa: E402
from scripts.lib.transcript import Corrections, Transcript  # noqa: E402


def _pick_engine(requested: str) -> str:
    if requested != "auto":
        return requested
    return "whisperx" if ffmpeg.have("whisperx") else "hyperframes"


def run_whisperx(audio: Path, out_dir: Path, model: str, language: str, dry_run: bool) -> Transcript:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "whisperx", str(audio), "--model", model, "--language", language,
        "--output_format", "json", "--output_dir", str(out_dir), "--print_progress", "True",
    ]
    if dry_run:
        print("[dry-run]", " ".join(cmd))
        return Transcript(words=[])
    if not ffmpeg.have("whisperx"):
        raise RuntimeError("whisperx not found. Use --engine hyperframes, or see docs/SETUP.md.")
    if subprocess.run(cmd, text=True).returncode != 0:
        raise RuntimeError("whisperx failed; see output above.")
    produced = out_dir / f"{audio.stem}.json"
    if not produced.is_file():
        jsons = sorted(out_dir.glob("*.json"))
        if not jsons:
            raise RuntimeError(f"whisperx produced no JSON in {out_dir}")
        produced = jsons[0]
    return Transcript.from_whisperx(produced)


def run_hyperframes(audio: Path, out_dir: Path, model: str, language: str, dry_run: bool) -> Transcript:
    hf_model = model if model not in ("large-v3",) else "large-v3"
    produced = hfa.transcribe(audio, out_dir, model=hf_model, language=language or None, dry_run=dry_run)
    if dry_run or produced is None:
        return Transcript(words=[])
    return Transcript.from_any(produced)


def main() -> int:
    ap = argparse.ArgumentParser(description="Transcribe the raw clip to word-level timestamps.")
    ap.add_argument("--job", required=True)
    ap.add_argument("--engine", default="auto", choices=["auto", "hyperframes", "whisperx"])
    ap.add_argument("--model", default="", help="ASR model (default: engine-specific — small.en / large-v3).")
    ap.add_argument("--language", default="en")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    job = project.Job.load(args.job)
    audio = job.directory / job.source
    if not audio.is_file():
        print(f"error: raw source missing: {audio}", file=sys.stderr)
        return 1

    engine = _pick_engine(args.engine)
    raw_dir = job.path("transcript", "_asr")
    if engine == "whisperx":
        model = args.model or "large-v3"
        t = run_whisperx(audio, raw_dir, model, args.language, args.dry_run)
    else:
        model = args.model or "small.en"
        t = run_hyperframes(audio, raw_dir, model, args.language, args.dry_run)

    if args.dry_run:
        print(f"[dry-run] engine={engine}; would normalize + apply corrections -> {job.corrected_json}")
        return 0

    if not t.words:
        print(f"error: {engine} produced an empty transcript.", file=sys.stderr)
        return 1
    t.save(job.transcript_json)

    corrections = Corrections.load(presets.corrections_path())
    changed = t.apply_corrections(corrections)
    t.save(job.corrected_json)

    job.set_stage("rough_cut", "transcribed", engine=engine, words=len(t.words), corrections_applied=changed)
    print(f"✓ transcribe [{engine}]: {len(t.words)} words, {t.duration:.1f}s, {changed} corrections applied")
    print("  next: python scripts/rough_cut.py --job", job.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

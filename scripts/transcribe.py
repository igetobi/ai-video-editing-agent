#!/usr/bin/env python3
"""Stage 2a — Transcribe with WhisperX (word-level timestamps).

    python scripts/transcribe.py --job "channel intro" [--model large-v3] [--language en]

Produces:
    transcript/transcript.json   normalized word-level transcript
    transcript/corrected.json    same, with caption-corrections applied

Word-level timestamps are what make precise, natural-language cutting possible
downstream, so alignment (WhisperX's job) matters more than model size.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import ffmpeg, presets, project  # noqa: E402
from scripts.lib.transcript import Corrections, Transcript  # noqa: E402


def run_whisperx(audio: Path, out_dir: Path, model: str, language: str, dry_run: bool) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "whisperx", str(audio),
        "--model", model,
        "--language", language,
        "--output_format", "json",
        "--output_dir", str(out_dir),
        "--print_progress", "True",
    ]
    if dry_run:
        print("[dry-run]", " ".join(cmd))
        return out_dir / f"{audio.stem}.json"
    if not ffmpeg.have("whisperx"):
        raise RuntimeError("whisperx not found. See scripts/doctor.sh / docs/SETUP.md.")
    proc = subprocess.run(cmd, text=True)
    if proc.returncode != 0:
        raise RuntimeError("whisperx failed; see output above.")
    produced = out_dir / f"{audio.stem}.json"
    if not produced.is_file():
        # WhisperX names output after the input stem; find any json as a fallback.
        jsons = sorted(out_dir.glob("*.json"))
        if not jsons:
            raise RuntimeError(f"whisperx produced no JSON in {out_dir}")
        produced = jsons[0]
    return produced


def main() -> int:
    ap = argparse.ArgumentParser(description="Transcribe the raw clip with WhisperX.")
    ap.add_argument("--job", required=True)
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--language", default="en")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    job = project.Job.load(args.job)
    audio = job.directory / job.source
    if not audio.is_file():
        print(f"error: raw source missing: {audio}", file=sys.stderr)
        return 1

    raw_dir = job.path("transcript", "_whisperx")
    produced = run_whisperx(audio, raw_dir, args.model, args.language, args.dry_run)
    if args.dry_run:
        print("[dry-run] would normalize + apply corrections ->", job.corrected_json)
        return 0

    t = Transcript.from_whisperx(produced)
    t.save(job.transcript_json)

    corrections = Corrections.load(presets.corrections_path())
    changed = t.apply_corrections(corrections)
    t.save(job.corrected_json)

    job.set_stage("rough_cut", "transcribed", words=len(t.words), corrections_applied=changed)
    print(f"✓ transcribe: {len(t.words)} words, {t.duration:.1f}s, {changed} corrections applied")
    print("  next: python scripts/rough_cut.py --job", job.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

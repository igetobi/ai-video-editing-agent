#!/usr/bin/env python3
"""Show pipeline status for a job (or list all jobs).

    python scripts/status.py                 # list all jobs
    python scripts/status.py --job "intro"   # detail for one job
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import project  # noqa: E402

MARK = {"done": "✓", "pending": "·", "planned": "◐", "transcribed": "◐"}


def show(job: project.Job) -> None:
    print(f"\n{job.name}  [{job.format}]  {job.width}x{job.height}@{job.fps}fps")
    print(f"  source: {job.source or '(none)'}")
    for stage, _ in project.STAGES:
        info = job.stages.get(stage, {})
        st = info.get("status", "pending")
        opt = " (optional)" if info.get("optional") else ""
        extra = ""
        if stage == "rough_cut" and "timeline_duration" in info:
            extra = f" — {info['timeline_duration']}s, {info.get('segments','?')} segs"
        if stage == "graphics" and "overlays" in info:
            extra = f" — {info['overlays']} overlays, {info.get('zooms',0)} zooms"
        print(f"    {MARK.get(st, '·')} {stage:<12}{opt} {st}{extra}")
    latest = job.latest_video()
    print(f"  latest render: {latest.name if latest else '(none)'}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Show job status.")
    ap.add_argument("--job")
    args = ap.parse_args()

    if args.job:
        show(project.Job.load(args.job))
        return 0

    pdir = project.projects_dir()
    jobs = sorted(d for d in pdir.glob("*/") if (d / "job.json").is_file())
    if not jobs:
        print("No jobs yet. Create one: python scripts/intake.py --source <clip> --name <title>")
        return 0
    for d in jobs:
        show(project.Job.load(str(d)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

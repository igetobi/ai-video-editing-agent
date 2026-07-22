#!/usr/bin/env python3
"""Stage 3b — Build graphics. Render each plan beat, then composite onto the cut.

    python scripts/build_graphics.py --job "channel intro" [--only b003 b004] [--dry-run]

Incremental by design: each beat carries an input_hash (its fields + the resolved
preset). A beat is re-rendered only if that hash changed or its clip is missing, so
moving one card re-renders one beat, not the whole video (the render cache in
graphics/.render-cache.json tracks this). Compositing then overlays the current beat
clips and applies any ken-burns 'zoom' beats to the base — this is the fast
iteration loop the second pass relies on.

Overlay beats  -> HyperFrames alpha clips composited at their timeline position.
Camera beats   -> 'zoom' punches into the base video for its window; 'transition'
                  is a marker (handled at export) — no clip.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import composition, hyperframes_adapter  # noqa: E402
from scripts.lib import ffmpeg, presets, project  # noqa: E402
from scripts.lib.cache import RenderCache  # noqa: E402
from scripts.lib.plan import Plan  # noqa: E402

CAMERA_KINDS = {"zoom", "transition"}


def _render_beats(job: project.Job, plan: Plan, only: set[str] | None, dry_run: bool):
    cache = RenderCache(job.render_cache)
    fingerprints: dict[str, str] = {}
    seg_dir = job.path("graphics", "segments")
    rendered, skipped = [], []

    for beat in plan.active():
        if only and beat.id not in only:
            continue
        if beat.preset not in fingerprints:
            _, fp = presets.resolve_style(beat.preset)
            fingerprints[beat.preset] = fp
        fp = fingerprints[beat.preset]
        h = beat.input_hash(fp)
        seg_file = seg_dir / f"{beat.id}.mov"

        if cache.is_fresh(beat.id, h, seg_file):
            skipped.append(beat.id)
            continue

        style, _ = presets.resolve_style(beat.preset)
        html = composition.build_composition(beat, style, plan.width, plan.height, plan.fps)
        html_path = job.path("graphics", "compositions", f"{beat.id}.html")
        if not dry_run:
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(html)
        hyperframes_adapter.render(html_path, seg_file, plan.fps, plan.width, plan.height, dry_run=dry_run)
        if not dry_run:
            cache.record(beat.id, h, seg_file)
        rendered.append(beat.id)

    removed = cache.prune({b.id for b in plan.active()})
    if not dry_run:
        cache.save()
    return rendered, skipped, removed


def _zoom_expr(zoom_beats, factor_default=1.08) -> str:
    expr = "1.0"
    for b in zoom_beats:
        f = float(b.params.get("zoom", factor_default))
        expr = f"if(between(t,{b.t_in:.3f},{b.t_out:.3f}),{f},{expr})"
    return expr


def _composite(job: project.Job, plan: Plan, dry_run: bool):
    base = job.rough_mp4
    if not base.is_file() and not dry_run:
        raise RuntimeError("cut/rough.mp4 missing — run rough_cut first.")

    overlays = [b for b in plan.active() if b.kind not in CAMERA_KINDS]
    zooms = [b for b in plan.beats if b.enabled and b.kind == "zoom"]
    W, H = plan.width, plan.height

    inputs = ["ffmpeg", "-y", "-i", str(base)]
    seg_dir = job.path("graphics", "segments")
    filters = []
    if zooms:
        z = _zoom_expr(zooms)
        crop = (f"crop=w='iw/({z})':h='ih/({z})':"
                f"x='(iw-iw/({z}))/2':y='(ih-ih/({z}))/2'")
        filters.append(f"[0:v]{crop},scale={W}:{H}:flags=bicubic,setsar=1[base]")
    else:
        filters.append("[0:v]setsar=1[base]")

    prev = "base"
    for i, b in enumerate(overlays, start=1):
        inputs += ["-i", str(seg_dir / f"{b.id}.mov")]
        filters.append(f"[{i}:v]setpts=PTS-STARTPTS+{b.t_in:.3f}/TB[ov{i}]")
        step = f"c{i}"
        filters.append(
            f"[{prev}][ov{i}]overlay=0:0:enable='between(t,{b.t_in:.3f},{b.t_out:.3f})':eof_action=pass[{step}]"
        )
        prev = step

    filtergraph = ";".join(filters)
    cmd = inputs + [
        "-filter_complex", filtergraph, "-map", f"[{prev}]", "-map", "0:a?",
        *ffmpeg.X264, "-c:a", "copy", str(job.composited_mp4),
    ]
    ffmpeg.run(cmd, dry_run=dry_run)
    return len(overlays), len(zooms)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render beats + composite graphics.")
    ap.add_argument("--job", required=True)
    ap.add_argument("--only", nargs="*", help="Restrict rendering to these beat ids (still composites all).")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    job = project.Job.load(args.job)
    if not job.plan_json.is_file():
        print("error: no plan.json — run plan_graphics.py first.", file=sys.stderr)
        return 1
    plan = Plan.load(job.plan_json)

    rendered, skipped, removed = _render_beats(job, plan, set(args.only) if args.only else None, args.dry_run)
    print(f"✓ beats: rendered {len(rendered)}, reused {len(skipped)} (cache), pruned {len(removed)}")
    if rendered:
        print("  rendered:", ", ".join(rendered[:12]) + (" ..." if len(rendered) > 12 else ""))

    n_ov, n_zoom = _composite(job, plan, args.dry_run)
    if not args.dry_run:
        job.set_stage("graphics", "done", overlays=n_ov, zooms=n_zoom)
        print(f"✓ composited {n_ov} overlays + {n_zoom} zooms -> {job.composited_mp4}")
        print("  second pass: tweak plan.json + re-run (only changed beats re-render).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

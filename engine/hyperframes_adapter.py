"""Adapter that renders HyperFrames compositions to alpha video clips.

Matches the real CLI (v0.7.68): a HyperFrames *project* is a directory containing
`hyperframes.json` + `index.html`; compositions live under `compositions/` and are
rendered with `hyperframes render <dir> -c compositions/<beat>.html -o <out>`.

We treat each job's `graphics/` directory as a HyperFrames project: `ensure_project`
synthesizes the minimal project files deterministically (no interactive `init`, no
network), and `render_beat` renders one composition to an alpha MOV.

Executable resolution: prefer the locally-installed bin
(`node_modules/hyperframes/bin/hyperframes.mjs`) invoked via `node`, which is robust
regardless of cwd; fall back to `npx hyperframes` if the package isn't vendored yet.
Flags live in engine/engine.json — the one place to adjust per version.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

_ENGINE_JSON = Path(__file__).with_name("engine.json")
_REPO_ROOT = Path(__file__).resolve().parents[1]


def _cfg() -> dict:
    return json.loads(_ENGINE_JSON.read_text())


def _base() -> list[str]:
    """The executable prefix for a hyperframes invocation."""
    binjs = _REPO_ROOT / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
    if binjs.is_file() and shutil.which("node"):
        return ["node", str(binjs)]
    return ["npx", "hyperframes"]  # fetches on first use if not vendored


def available() -> bool:
    binjs = _REPO_ROOT / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
    return (binjs.is_file() and shutil.which("node") is not None) or shutil.which("npx") is not None


def ensure_project(project_dir: Path, name: str) -> None:
    """Write the minimal HyperFrames project files if they don't exist."""
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "compositions").mkdir(exist_ok=True)
    (project_dir / "assets").mkdir(exist_ok=True)

    hf = project_dir / "hyperframes.json"
    if not hf.is_file():
        hf.write_text(json.dumps({
            "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
            "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
            "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
            "media": {"autoProxy": True},
        }, indent=2) + "\n")

    meta = project_dir / "meta.json"
    if not meta.is_file():
        meta.write_text(json.dumps({"id": name, "name": name}, indent=2) + "\n")

    idx = project_dir / "index.html"
    if not idx.is_file():
        idx.write_text(
            '<!doctype html>\n<html lang="en"><head><meta charset="UTF-8"/>\n'
            '<meta name="viewport" content="width=1920, height=1080"/></head>\n'
            '<body><div id="root" data-composition-id="index" data-start="0" '
            'data-duration="1" data-width="1920" data-height="1080"></div></body></html>\n'
        )


def _fps_arg(fps: float) -> str:
    return str(int(fps)) if float(fps) == int(fps) else str(fps)


def build_render_command(project_dir: Path, composition_rel: str, out_path: Path, fps: float) -> list[str]:
    r = _cfg()["render"]
    cmd = _base() + ["render", str(project_dir)]
    cmd += [r["composition_flag"], composition_rel]
    cmd += [r["output_flag"], str(out_path)]
    cmd += [r["format_flag"], r.get("format", "mov")]
    cmd += [r["fps_flag"], _fps_arg(fps)]
    if r.get("quality"):
        cmd += [r["quality_flag"], r["quality"]]
    cmd += list(r.get("extra_args", []))
    return cmd


def render_beat(
    project_dir: Path, beat_id: str, out_path: Path, fps: float, dry_run: bool = False,
) -> Optional[Path]:
    """Render compositions/<beat_id>.html -> out_path (alpha MOV). None on dry-run."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_render_command(project_dir, f"compositions/{beat_id}.html", out_path, fps)
    printable = " ".join(cmd)
    if dry_run:
        print(f"[dry-run] {printable}")
        return None
    if not available():
        raise RuntimeError("Node/npx not found — HyperFrames needs Node 22+. Run scripts/doctor.sh.")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"HyperFrames render failed:\n{printable}\n{proc.stderr[-2000:]}")
    return out_path


def ensure_browser(dry_run: bool = False) -> None:
    """Install/cache Chrome Headless Shell for local rendering (idempotent)."""
    cmd = _base() + ["browser", "ensure"]
    if dry_run:
        print("[dry-run]", " ".join(cmd))
        return
    subprocess.run(cmd, capture_output=True, text=True)


def transcribe(
    audio: Path, project_dir: Path, model: str = "small.en",
    language: Optional[str] = None, dry_run: bool = False,
) -> Optional[Path]:
    """Transcribe with HyperFrames' bundled engine (whisper.cpp/Parakeet, word-level).

    Returns the path to a transcript JSON to normalize with Transcript.from_any.
    Lighter than WhisperX (no PyTorch); needs a whisper.cpp binary on PATH
    (macOS: `brew install whisper-cpp`; Linux: build from source or use our image).
    """
    project_dir.mkdir(parents=True, exist_ok=True)
    t = _cfg().get("transcribe", {})
    cmd = _base() + ["transcribe", str(audio), t.get("dir_flag", "-d"), str(project_dir), t.get("json_flag", "--json")]
    if model:
        cmd += [t.get("model_flag", "-m"), model]
    if language:
        cmd += ["-l", language]
    if dry_run:
        print("[dry-run]", " ".join(cmd))
        return None
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"HyperFrames transcribe failed:\n{' '.join(cmd)}\n{proc.stderr[-2000:] or proc.stdout[-2000:]}")

    # Preferred: stdout is a JSON document with the transcript inline.
    out_json = project_dir / "hf-transcribe.json"
    stdout = proc.stdout.strip()
    if stdout.startswith("{") or stdout.startswith("["):
        try:
            data = json.loads(stdout)
            if _looks_like_transcript(data):
                out_json.write_text(json.dumps(data))
                return out_json
        except json.JSONDecodeError:
            pass
    # Fallback: HyperFrames wrote a transcript file into the project dir.
    candidates = sorted(project_dir.rglob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for c in candidates:
        try:
            if _looks_like_transcript(json.loads(c.read_text())):
                return c
        except (json.JSONDecodeError, OSError):
            continue
    raise RuntimeError(f"HyperFrames transcribe produced no recognizable transcript in {project_dir}")


def _looks_like_transcript(data) -> bool:
    if isinstance(data, list):
        return bool(data) and isinstance(data[0], dict) and ("word" in data[0] or "text" in data[0])
    if not isinstance(data, dict):
        return False
    for key in ("transcript", "result", "data", "output"):
        if isinstance(data.get(key), dict):
            data = data[key]
            break
    return bool(data.get("words") or data.get("segments"))

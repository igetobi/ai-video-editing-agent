"""Thin, inspectable ffmpeg / ffprobe wrappers.

Design goals:
  * Every command is *built* as a list and can be printed (``--dry-run``) so the
    exact ffmpeg invocation is auditable and unit-testable without ffmpeg present.
  * Filters we rely on (concat, overlay, loudnorm, sidechaincompress, subtitles)
    are wrapped in small named helpers so the pipeline reads at a high level.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


class FFmpegError(RuntimeError):
    pass


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def _fmt(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(c)) for c in cmd)


def run(cmd: Sequence[str], dry_run: bool = False, quiet: bool = False) -> str:
    """Run a command list. In dry_run mode, print and return the command string."""
    printable = _fmt(cmd)
    if dry_run:
        print(f"[dry-run] {printable}")
        return printable
    if not have(cmd[0]):
        raise FFmpegError(
            f"'{cmd[0]}' is not installed. Run `scripts/doctor.sh` for setup help."
        )
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(f"Command failed ({proc.returncode}):\n{printable}\n{proc.stderr[-2000:]}")
    if not quiet and proc.stderr:
        # ffmpeg logs to stderr even on success; surface the tail only.
        pass
    return proc.stdout


# ---- probing ----------------------------------------------------------
@dataclass
class MediaInfo:
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool


def probe(path: Path) -> MediaInfo:
    """Return basic media info via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    if not have("ffprobe"):
        raise FFmpegError("'ffprobe' is not installed. Run `scripts/doctor.sh`.")
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise FFmpegError(f"ffprobe failed for {path}:\n{out.stderr[-1000:]}")
    data = json.loads(out.stdout)
    v = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    duration = float(data.get("format", {}).get("duration", 0.0))
    width = int(v["width"]) if v else 0
    height = int(v["height"]) if v else 0
    fps = 30.0
    if v and v.get("r_frame_rate", "0/0") not in ("0/0", "0"):
        num, _, den = v["r_frame_rate"].partition("/")
        try:
            fps = float(num) / float(den or 1)
        except ZeroDivisionError:
            fps = 30.0
    return MediaInfo(duration=duration, width=width, height=height, fps=round(fps, 3), has_audio=a is not None)


# ---- common operations ------------------------------------------------
X264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
AAC = ["-c:a", "aac", "-b:a", "256k"]


def extract_segment(src: Path, dst: Path, ss: float, to: float, reencode: bool = True) -> list[str]:
    """Build a command to cut [ss, to] out of src. Re-encode for frame accuracy."""
    cmd = ["ffmpeg", "-y", "-ss", f"{ss:.3f}", "-to", f"{to:.3f}", "-i", str(src)]
    cmd += X264 + AAC if reencode else ["-c", "copy"]
    cmd += [str(dst)]
    return cmd


def concat_demux(list_file: Path, dst: Path, reencode: bool = False) -> list[str]:
    """Concat pre-cut segments listed in a concat-demuxer file."""
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file)]
    cmd += (X264 + AAC) if reencode else ["-c", "copy"]
    cmd += [str(dst)]
    return cmd


def _fit_filter(w: int, h: int, fit: str = "cover") -> str:
    """Scale+crop ('cover') or scale+pad ('contain') to WxH with square pixels."""
    if not w or not h:
        return "setsar=1"
    if fit == "contain":
        return (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1")
    return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"


def trim_concat(
    src: Path, spans: list[tuple[float, float]], dst: Path, fps: float,
    width: int = 0, height: int = 0, fit: str = "cover", has_audio: bool = True,
) -> list[str]:
    """Single-pass, frame-accurate trim of source spans concatenated into one clip.

    Uses trim/atrim filters (not -ss seeking) so cuts land exactly on the
    word-level timestamps. Hard cuts (no blending).
    """
    scale = ("," + _fit_filter(width, height, fit)) if (width and height) else ",setsar=1"
    vf, af = [], []
    for i, (a, b) in enumerate(spans):
        vf.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS,fps={fps}{scale}[v{i}]")
        if has_audio:
            af.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}]")
    n = len(spans)
    if has_audio:
        pairs = "".join(f"[v{i}][a{i}]" for i in range(n))
        concat = f"{pairs}concat=n={n}:v=1:a=1[outv][outa]"
        maps = ["-map", "[outv]", "-map", "[outa]"]
    else:
        vs = "".join(f"[v{i}]" for i in range(n))
        concat = f"{vs}concat=n={n}:v=1:a=0[outv]"
        maps = ["-map", "[outv]"]
    filt = ";".join(vf + af + [concat])
    return ["ffmpeg", "-y", "-i", str(src), "-filter_complex", filt, *maps, "-r", str(fps), *X264, *AAC, str(dst)]


def trim_concat_smooth(
    src: Path, spans: list[tuple[float, float]], dst: Path, fps: float,
    transition: float = 0.13, width: int = 0, height: int = 0, fit: str = "cover",
) -> list[str]:
    """Like trim_concat, but cross-dissolves (video) + crossfades (audio) each seam.

    The per-join transition is clamped to 45% of the shorter neighbouring segment so
    short segments never break the xfade chain. Talking-head cuts read as smooth
    instead of hard jumps.
    """
    scale = ("," + _fit_filter(width, height, fit)) if (width and height) else ",setsar=1"
    durs = [b - a for a, b in spans]
    parts = []
    for i, (a, b) in enumerate(spans):
        parts.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS,fps={fps}{scale},format=yuv420p,settb=AVTB[v{i}]")
        parts.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo[a{i}]")
    vcur, acur, vlen = "v0", "a0", durs[0]
    for i in range(1, len(spans)):
        t = max(0.04, min(transition, 0.45 * min(durs[i - 1], durs[i])))
        off = max(0.0, vlen - t)
        parts.append(f"[{vcur}][v{i}]xfade=transition=fade:duration={t:.3f}:offset={off:.3f}[vx{i}]")
        parts.append(f"[{acur}][a{i}]acrossfade=d={t:.3f}[ax{i}]")
        vcur, acur = f"vx{i}", f"ax{i}"
        vlen = vlen + durs[i] - t
    return ["ffmpeg", "-y", "-i", str(src), "-filter_complex", ";".join(parts),
            "-map", f"[{vcur}]", "-map", f"[{acur}]", "-r", str(fps), *X264, *AAC, str(dst)]


def loudnorm(src: Path, dst: Path, i: float = -16.0, tp: float = -1.5, lra: float = 11.0) -> list[str]:
    """EBU R128 loudness normalization (voice)."""
    return [
        "ffmpeg", "-y", "-i", str(src),
        "-af", f"loudnorm=I={i}:TP={tp}:LRA={lra}",
        "-c:v", "copy", *AAC, str(dst),
    ]


def overlay_alpha(base: Path, overlay: Path, dst: Path, t_in: float, t_out: float) -> list[str]:
    """Overlay an alpha (mov/webm) clip on ``base`` between t_in and t_out."""
    filt = (
        f"[1:v]setpts=PTS-STARTPTS+{t_in}/TB[ov];"
        f"[0:v][ov]overlay=0:0:enable='between(t,{t_in},{t_out})':eof_action=pass[v]"
    )
    return [
        "ffmpeg", "-y", "-i", str(base), "-i", str(overlay),
        "-filter_complex", filt, "-map", "[v]", "-map", "0:a?",
        *X264, "-c:a", "copy", str(dst),
    ]


def burn_subtitles(src: Path, ass: Path, dst: Path, fonts_dir: Optional[Path] = None) -> list[str]:
    """Burn an .ass caption track into the video."""
    filt = f"subtitles={shlex.quote(str(ass))}"
    if fonts_dir:
        filt += f":fontsdir={shlex.quote(str(fonts_dir))}"
    return ["ffmpeg", "-y", "-i", str(src), "-vf", filt, *X264, "-c:a", "copy", str(dst)]


def add_music_ducked(
    voice_video: Path, music: Path, dst: Path,
    music_gain_db: float = -23.0, duck_threshold: float = 0.05,
    duck_ratio: float = 8.0, final_lufs: float = -14.0,
) -> list[str]:
    """Mix background music under the voice, side-chain ducking under speech.

    ``music_gain_db`` sets the resting music level; ducking pulls it down further
    whenever the voice is present, then the whole mix is re-normalized to
    ``final_lufs`` (three-stage loudness: voice -16, bed ducked, final -14).
    """
    filt = (
        f"[1:a]volume={music_gain_db}dB[bg];"
        f"[bg][0:a]sidechaincompress=threshold={duck_threshold}:ratio={duck_ratio}:attack=20:release=400[duck];"
        f"[0:a][duck]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
        f"loudnorm=I={final_lufs}:TP=-1.5:LRA=11[a]"
    )
    return [
        "ffmpeg", "-y", "-i", str(voice_video), "-stream_loop", "-1", "-i", str(music),
        "-filter_complex", filt, "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", *AAC, "-shortest", str(dst),
    ]


def thumbnail_frame(src: Path, dst: Path, t: float) -> list[str]:
    return ["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", "-q:v", "2", str(dst)]


def scale_pad(src: Path, dst: Path, width: int, height: int) -> list[str]:
    """Fit source into WxH (letterbox/pillarbox), e.g. reframe 16:9 -> 9:16."""
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    )
    return ["ffmpeg", "-y", "-i", str(src), "-vf", vf, *X264, *AAC, str(dst)]

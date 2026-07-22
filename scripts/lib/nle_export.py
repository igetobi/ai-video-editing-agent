"""NLE off-ramp builders — turn a cut-list (EDL model) into files a traditional
editor can import. This is the "to-premiere" escape hatch: rough-cut in the agent,
then finish by hand in Premiere / Resolve / Final Cut if you want to.

Two formats, both built as pure strings (unit-testable, no external tools):
  * CMX3600 EDL  (.edl) — the universal interchange; imports into Premiere, Resolve,
                          Avid, Final Cut. Single video reel + stereo audio.
  * FCPXML 1.9   (.fcpxml) — richer, keeps clip names; imports into Premiere & FCP.
"""

from __future__ import annotations

from xml.sax.saxutils import escape as _xesc

from .edl import EDL


def _tc(seconds: float, fps: float) -> str:
    """Seconds -> HH:MM:SS:FF (non-drop) at the given fps."""
    fps_i = int(round(fps))
    total_frames = int(round(seconds * fps_i))
    frames = total_frames % fps_i
    total_secs = total_frames // fps_i
    s = total_secs % 60
    m = (total_secs // 60) % 60
    h = total_secs // 3600
    return f"{h:02d}:{m:02d}:{s:02d}:{frames:02d}"


def build_cmx3600_edl(edl: EDL, title: str, reel: str = "AX") -> str:
    """Build a CMX3600 EDL. Record times accumulate along the timeline."""
    lines = [f"TITLE: {title}", "FCM: NON-DROP FRAME", ""]
    rec = 0.0
    clip_name = edl.source.split("/")[-1]
    for i, seg in enumerate(edl.segments, start=1):
        src_in = _tc(seg.src_in, edl.fps)
        src_out = _tc(seg.src_out, edl.fps)
        rec_in = _tc(rec, edl.fps)
        rec_out = _tc(rec + seg.duration, edl.fps)
        n = f"{i:03d}"
        lines.append(f"{n}  {reel:<7} V     C        {src_in} {src_out} {rec_in} {rec_out}")
        lines.append(f"* FROM CLIP NAME: {clip_name}")
        lines.append(f"{n}  {reel:<7} AA    C        {src_in} {src_out} {rec_in} {rec_out}")
        rec += seg.duration
    return "\n".join(lines) + "\n"


def build_fcpxml(edl: EDL, title: str, width: int, height: int) -> str:
    """Build a minimal FCPXML 1.9 document for the cut list."""
    fps_i = int(round(edl.fps))
    # FCPXML uses rational frame durations, e.g. 30fps -> 1/30s.
    frame_dur = f"1/{fps_i}s"
    clip_name = _xesc(edl.source.split("/")[-1])

    def d(seconds: float) -> str:
        return f"{int(round(seconds * fps_i))}/{fps_i}s"

    spine = []
    offset = 0.0
    for seg in edl.segments:
        spine.append(
            f'          <asset-clip ref="r2" name="{clip_name}" '
            f'offset="{d(offset)}" duration="{d(seg.duration)}" start="{d(seg.src_in)}" '
            f'format="r1" tcFormat="NDF"/>'
        )
        offset += seg.duration
    spine_xml = "\n".join(spine)
    total = d(edl.timeline_duration)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9">
  <resources>
    <format id="r1" name="FFVideoFormat" frameDuration="{frame_dur}" width="{width}" height="{height}"/>
    <asset id="r2" name="{clip_name}" hasVideo="1" hasAudio="1" format="r1" src="{_xesc(edl.source)}"/>
  </resources>
  <library>
    <event name="{_xesc(title)}">
      <project name="{_xesc(title)}">
        <sequence format="r1" tcFormat="NDF">
          <spine>
{spine_xml}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
""".replace("__TOTAL__", total)

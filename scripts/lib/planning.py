"""Pure logic to scaffold a graphics Plan from the cut + transcript.

This produces sensibly-timed *placeholder* beats aligned to the rough-cut timeline
and the chosen format. The graphics-plan skill then rewrites the copy, kinds, and
assets — this just gives Claude a correct timing skeleton to work from so it never
has to guess timeline math.
"""

from __future__ import annotations

from typing import Any

from .edl import EDL
from .plan import Beat, Plan
from .transcript import Transcript


def _timeline_words(edl: EDL, t: Transcript) -> list[tuple[float, float, str]]:
    """Map transcript words onto the output timeline: (t_in, t_out, text)."""
    out: list[tuple[float, float, str]] = []
    offset = 0.0
    for seg in edl.segments:
        ws, we = seg.word_start, seg.word_end
        if ws is None or we is None:
            offset += seg.duration
            continue
        for w in t.words[ws:we]:
            ti = offset + max(0.0, w.start - seg.src_in)
            to = offset + max(0.0, w.end - seg.src_in)
            out.append((ti, min(to, offset + seg.duration), w.text))
        offset += seg.duration
    return out


def _sentences(tl_words: list[tuple[float, float, str]], gap_split: float = 0.6):
    sents = []
    cur: list[tuple[float, float, str]] = []
    for i, tw in enumerate(tl_words):
        cur.append(tw)
        ends_punct = tw[2].strip().endswith((".", "!", "?"))
        big_gap = (i + 1 < len(tl_words)) and (tl_words[i + 1][0] - tw[1] > gap_split)
        if ends_punct or big_gap or i == len(tl_words) - 1:
            if cur:
                sents.append({
                    "t_in": cur[0][0],
                    "t_out": cur[-1][1],
                    "text": " ".join(w[2] for w in cur).strip(),
                })
                cur = []
    return sents


def _gist(text: str, max_words: int = 6) -> str:
    words = text.strip().strip(".,!?").split()
    return " ".join(words[:max_words])


def build_plan(edl: EDL, t: Transcript, fmt: dict[str, Any], fmt_name: str,
               width: int, height: int, fps: float, bpm_target: float = 8.0) -> Plan:
    tl = _timeline_words(edl, t)
    sents = _sentences(tl)
    duration = edl.timeline_duration
    default_preset = fmt.get("graphics", {}).get("default_preset", "signature-style")
    layout = fmt.get("graphics", {}).get("layout", "fullscreen")

    plan = Plan(format=fmt_name, fps=fps, width=width, height=height, beats=[])
    plan.meta = {"scaffold": True, "note": "Placeholder beats — refine copy/kind/assets, then build."}

    if not sents:
        return plan

    # Density cap: keep the strongest N sentences, always keep the first.
    target = max(1, int(round(duration / 60.0 * bpm_target)))
    if fmt_name.startswith("short"):
        target = max(target, len(sents))  # short-form is graphic-dense
    chosen = sents
    if len(sents) > target:
        ranked = sorted(range(len(sents)), key=lambda i: (sents[i]["t_out"] - sents[i]["t_in"]), reverse=True)
        keep = set(ranked[:target]) | {0}
        chosen = [s for i, s in enumerate(sents) if i in keep]

    if fmt_name == "short-tiktok":
        # Bold hook on the first sentence, then leave the rest raw.
        s0 = chosen[0]
        plan.beats.append(Beat(
            id="b000", kind="hook-card", t_in=s0["t_in"], t_out=min(s0["t_out"], s0["t_in"] + 2.5),
            title=_gist(s0["text"], 8).upper(), position="top", preset=default_preset,
            note="hook — rewrite punchy",
        ))
        return plan

    kind = "top-card" if layout == "top-half" else "lower-third"
    position = "top" if layout == "top-half" else "bottom"
    for i, s in enumerate(chosen):
        end = min(s["t_out"], s["t_in"] + 5.0)
        plan.beats.append(Beat(
            id=f"b{i:03d}", kind=kind, t_in=round(s["t_in"], 2), t_out=round(end, 2),
            title=_gist(s["text"]), subtitle="", position=position, preset=default_preset,
            note="PLACEHOLDER — refine copy",
        ))
    return plan

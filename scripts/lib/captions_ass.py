"""Word-level animated caption builder -> ASS subtitle file (burned in by ffmpeg).

Why ASS instead of the HyperFrames caption skill? For talking-head captions the
signature look is "each word appears on-beat as it's spoken, with the active word
highlighted". WhisperX already gives us exact word timings, so we can express that
deterministically in ASS and let ffmpeg burn it in one pass — no per-frame render,
no re-transcription. It is fast, precise, and matches the demo's caption style.

The builder is pure (no ffmpeg): given words + a captions preset it returns ASS
text, which makes it unit-testable and easy to eyeball.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .transcript import Word


def _ass_color(hex_color: str, alpha: float = 1.0) -> str:
    """#RRGGBB (+ alpha 0..1 opaque..transparent-at-0) -> ASS &HAABBGGRR."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = h[0:2], h[2:4], h[4:6]
    a = int(round((1.0 - max(0.0, min(1.0, alpha))) * 255))
    return f"&H{a:02X}{b}{g}{r}".upper()


def _escape(text: str) -> str:
    return text.replace("{", "(").replace("}", ")").replace("\n", " ")


@dataclass
class Card:
    words: list[Word]

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end


def _wrap_into_cards(words: list[Word], max_lines: int, max_chars: int) -> list[Card]:
    """Chunk words into caption cards, each up to max_lines lines of ~max_chars."""
    cards: list[Card] = []
    current: list[Word] = []
    line_len = 0
    lines_used = 1
    for w in words:
        add = len(w.text) + (1 if current else 0)
        if line_len + add > max_chars:
            if lines_used >= max_lines:
                cards.append(Card(current))
                current, line_len, lines_used = [], 0, 1
            else:
                lines_used += 1
                line_len = 0
        current.append(w)
        line_len += add
    if current:
        cards.append(Card(current))
    return cards


def _layout_lines(card_words: list[Word], max_chars: int) -> list[list[int]]:
    """Return line groupings (indices into card_words) for rendering \\N breaks."""
    lines: list[list[int]] = [[]]
    line_len = 0
    for i, w in enumerate(card_words):
        add = len(w.text) + (1 if lines[-1] else 0)
        if line_len + add > max_chars and lines[-1]:
            lines.append([])
            line_len = 0
        lines[-1].append(i)
        line_len += add
    return lines


def build_ass(
    words: list[Word],
    preset: dict[str, Any],
    width: int,
    height: int,
    position_override: Optional[str] = None,
) -> str:
    """Render caption words into an ASS document string."""
    size = int(preset.get("size", 72))
    font = str(preset.get("font", "Arial")).split(",")[0].strip().strip("'\"")
    primary = _ass_color(preset.get("color", "#FFFFFF"))
    highlight = _ass_color(preset.get("highlight_color", preset.get("color", "#FFFFFF")))
    all_caps = bool(preset.get("all_caps", False))
    max_lines = int(preset.get("max_lines", 2))
    max_chars = int(preset.get("max_chars_per_line", 24))
    per_word = bool(preset.get("per_word", True))
    highlight_mode = preset.get("highlight_mode", "active-word")

    box = preset.get("box", {}) or {}
    box_on = bool(box.get("enabled", False))
    box_color = _ass_color(box.get("color", "#000000"), float(box.get("opacity", 0.85)))
    stroke = preset.get("stroke", {}) or {}
    stroke_on = bool(stroke.get("enabled", False))
    outline = float(stroke.get("width", 0)) if stroke_on else (0 if box_on else 2)
    outline_color = _ass_color(stroke.get("color", "#000000"))

    # Positioning.
    position = position_override or preset.get("position", "center")
    if position == "center":
        an, y = 5, int(height * 0.46)
    elif position in ("low", "bottom"):
        an, y = 2, int(height * 0.86)
    elif position == "top":
        an, y = 8, int(height * 0.14)
    else:  # numeric fraction as string
        try:
            an, y = 5, int(height * float(position))
        except (TypeError, ValueError):
            an, y = 5, int(height * 0.46)
    x = width // 2

    # BorderStyle 3 draws an opaque box (BackColour); 1 is outline+shadow.
    border_style = 3 if box_on else 1
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},{primary},{primary},{outline_color},{box_color},{1 if preset.get('weight',700)>=600 else 0},0,0,0,100,100,0,0,{border_style},{outline},1,{an},40,40,60,1

[Events]
Format: Layer, Start, End, Style, MarginL, MarginR, MarginV, Effect, Text
"""

    cards = _wrap_into_cards(words, max_lines, max_chars)
    events: list[str] = []

    def fmt_t(t: float) -> str:
        cs = int(round(t * 100))
        h, cs = divmod(cs, 360000)
        m, cs = divmod(cs, 6000)
        s, cs = divmod(cs, 100)
        return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"

    def render_text(card_words: list[Word], active_idx: int, revealed_upto: int) -> str:
        lines = _layout_lines(card_words, max_chars)
        out_lines: list[str] = []
        for line in lines:
            toks: list[str] = []
            for i in line:
                if per_word and i > revealed_upto:
                    continue  # not spoken yet -> hidden
                txt = card_words[i].text
                txt = txt.upper() if all_caps else txt
                txt = _escape(txt)
                if highlight_mode == "active-word" and i == active_idx:
                    toks.append(f"{{\\c{highlight}}}{txt}{{\\c{primary}}}")
                elif highlight_mode == "cumulative" and i <= active_idx:
                    toks.append(f"{{\\c{highlight}}}{txt}{{\\c{primary}}}")
                else:
                    toks.append(txt)
            if toks:
                out_lines.append(" ".join(toks))
        return "\\N".join(out_lines)

    pos_tag = f"{{\\pos({x},{y})\\an{an}\\fad(120,80)}}"
    for card in cards:
        cw = card.words
        if not per_word:
            text = pos_tag + render_text(cw, active_idx=len(cw) - 1, revealed_upto=len(cw) - 1)
            events.append(f"Dialogue: 0,{fmt_t(card.start)},{fmt_t(card.end + 0.15)},Cap,,0,0,0,,{text}")
            continue
        # One event per word onset: reveal words up to i, highlight word i.
        for i, w in enumerate(cw):
            start = w.start
            end = cw[i + 1].start if i + 1 < len(cw) else (card.end + 0.20)
            text = pos_tag + render_text(cw, active_idx=i, revealed_upto=i)
            events.append(f"Dialogue: 0,{fmt_t(start)},{fmt_t(end)},Cap,,0,0,0,,{text}")

    return header + "\n".join(events) + "\n"

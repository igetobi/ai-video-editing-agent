import unittest

import tests._bootstrap  # noqa: F401
from scripts.lib.captions_ass import _ass_color, build_ass
from scripts.lib.transcript import Word

PRESET = {
    "size": 72, "font": "Coolvetica", "color": "#FFFFFF", "highlight_color": "#E07A3F",
    "max_lines": 2, "max_chars_per_line": 20, "per_word": True, "highlight_mode": "active-word",
    "box": {"enabled": True, "color": "#000000", "opacity": 0.85, "radius": 14},
    "position": "center", "weight": 700,
}


class TestCaptions(unittest.TestCase):
    def test_ass_color_conversion(self):
        # #E07A3F -> &H00 BB GG RR = &H003F7AE0
        self.assertEqual(_ass_color("#E07A3F"), "&H003F7AE0")
        # 50% alpha -> AA = 0x80
        self.assertTrue(_ass_color("#FFFFFF", 0.5).startswith("&H80"))

    def test_build_ass_structure(self):
        words = [Word("Hello", 0.0, 0.4), Word("there", 0.45, 0.9), Word("friend", 0.95, 1.4)]
        ass = build_ass(words, PRESET, 1080, 1920)
        self.assertIn("[Script Info]", ass)
        self.assertIn("PlayResX: 1080", ass)
        self.assertIn("[Events]", ass)
        # per-word reveal => one Dialogue per word onset
        self.assertEqual(ass.count("Dialogue:"), 3)
        self.assertIn("Hello", ass)
        self.assertIn("friend", ass)
        # active-word highlight uses the highlight colour override
        self.assertIn("\\c&H", ass)

    def test_positions(self):
        words = [Word("a", 0.0, 0.3)]
        self.assertIn("\\an2", build_ass(words, PRESET, 1080, 1920, position_override="low"))
        self.assertIn("\\an8", build_ass(words, PRESET, 1080, 1920, position_override="top"))
        self.assertIn("\\an5", build_ass(words, PRESET, 1080, 1920, position_override="center"))

    def test_braces_escaped_in_text(self):
        words = [Word("a{b}c", 0.0, 0.3)]
        ass = build_ass(words, PRESET, 1080, 1920)
        # our own override tags use braces, but the word's braces must be neutralized
        self.assertNotIn("a{b}c", ass)
        self.assertIn("a(b)c", ass)


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from engine.composition import build_composition
from scripts.lib.plan import Beat
from scripts.lib.transcript import Corrections, Transcript, Word, find_word_index


class TestTranscript(unittest.TestCase):
    def test_from_whisperx_normalizes(self):
        data = {"language": "en", "segments": [
            {"start": 0.0, "end": 1.0, "text": "hi there",
             "words": [{"word": "hi", "start": 0.0, "end": 0.4, "score": 0.9},
                       {"word": "there", "start": 0.5, "end": 1.0, "score": 0.8}]},
        ]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "wx.json"
            p.write_text(json.dumps(data))
            t = Transcript.from_whisperx(p)
        self.assertEqual([w.text for w in t.words], ["hi", "there"])
        self.assertAlmostEqual(t.duration, 1.0)

    def test_corrections_preserve_punctuation_and_case(self):
        c = Corrections(replace={"hyperframes": "HyperFrames", "clod": "Claude"},
                        regex=[{"pattern": r"\bai\b", "replace": "AI", "flags": "i"}])
        self.assertEqual(c.fix("hyperframes."), "HyperFrames.")
        self.assertEqual(c.fix("Clod,"), "Claude,")
        self.assertEqual(c.fix("ai"), "AI")
        self.assertEqual(c.fix("hello"), "hello")

    def test_apply_corrections_counts(self):
        t = Transcript(words=[Word("hyperframes", 0, 1), Word("is", 1, 2), Word("clod", 2, 3)])
        c = Corrections(replace={"hyperframes": "HyperFrames", "clod": "Claude"})
        changed = t.apply_corrections(c)
        self.assertEqual(changed, 2)
        self.assertEqual(t.words[0].text, "HyperFrames")

    def test_find_word_index_nearest(self):
        words = [Word("go", 0, 1), Word("go", 10, 11)]
        self.assertEqual(find_word_index(words, "go", near=9.5), 1)
        self.assertEqual(find_word_index(words, "go", near=0.2), 0)


class TestComposition(unittest.TestCase):
    def test_builds_html_with_timing(self):
        beat = Beat(id="b007", t_in=1.0, t_out=4.0, kind="lower-third",
                    title="Hello", subtitle="World", body=["one", "two"])
        preset = {"card": {"accent": "#E07A3F", "radius": 24}, "type": {}, "animation": {}}
        html = build_composition(beat, preset, 1920, 1080, 30)
        self.assertIn("data-composition-id=\"b007\"", html)
        self.assertIn("data-duration=\"3.0\"", html)
        self.assertIn("Hello", html)
        self.assertIn("<li>one</li>", html)
        self.assertIn("background:transparent", html.replace(" ", "") or html)

    def test_html_escapes_content(self):
        beat = Beat(id="b0", t_in=0, t_out=1, title="a<b>&c")
        html = build_composition(beat, {"type": {}, "animation": {}, "card": {}}, 1920, 1080, 30)
        self.assertIn("a&lt;b&gt;&amp;c", html)


if __name__ == "__main__":
    unittest.main()

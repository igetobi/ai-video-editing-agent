import tempfile
import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from scripts.lib.cache import RenderCache
from scripts.lib.edl import EDL, Segment
from scripts.lib.plan import Beat, Plan
from scripts.lib.planning import build_plan
from scripts.lib.transcript import Transcript, Word


class TestPlanHashing(unittest.TestCase):
    def test_hash_changes_with_content(self):
        b = Beat(id="b0", t_in=0, t_out=2, title="Hi")
        h1 = b.input_hash("fp1")
        b.title = "Hello"
        h2 = b.input_hash("fp1")
        self.assertNotEqual(h1, h2)

    def test_hash_changes_with_preset_fingerprint(self):
        b = Beat(id="b0", t_in=0, t_out=2, title="Hi")
        self.assertNotEqual(b.input_hash("fp1"), b.input_hash("fp2"))

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Plan(beats=[Beat(id="b0", t_in=0, t_out=2, title="Hi", body=["x", "y"])])
            path = Path(d) / "plan.json"
            p.save(path)
            loaded = Plan.load(path)
            self.assertEqual(loaded.beats[0].title, "Hi")
            self.assertEqual(loaded.beats[0].body, ["x", "y"])


class TestRenderCache(unittest.TestCase):
    def test_freshness(self):
        with tempfile.TemporaryDirectory() as d:
            seg = Path(d) / "b0.mov"
            seg.write_text("x")  # pretend-rendered
            cache = RenderCache(Path(d) / ".cache.json")
            self.assertFalse(cache.is_fresh("b0", "hash1", seg))
            cache.record("b0", "hash1", seg)
            self.assertTrue(cache.is_fresh("b0", "hash1", seg))
            self.assertFalse(cache.is_fresh("b0", "hash2", seg))  # changed hash
            seg.unlink()
            self.assertFalse(cache.is_fresh("b0", "hash1", seg))  # missing file
            self.assertEqual(cache.prune(set()), ["b0"])


class TestPlanning(unittest.TestCase):
    def test_build_plan_produces_beats(self):
        edl = EDL(source="raw/x.mp4", fps=30, segments=[
            Segment(id="s000", src_in=0.0, src_out=3.0, text="First sentence here.",
                    word_start=0, word_end=3),
            Segment(id="s001", src_in=5.0, src_out=8.0, text="Second point now.",
                    word_start=3, word_end=6),
        ])
        t = Transcript(words=[
            Word("First", 0.0, 0.5), Word("sentence", 0.6, 1.2), Word("here.", 1.3, 2.9),
            Word("Second", 5.1, 5.6), Word("point", 5.7, 6.3), Word("now.", 6.4, 7.8),
        ])
        fmt = {"graphics": {"default_preset": "signature-style", "layout": "top-half"}}
        plan = build_plan(edl, t, fmt, "short-explainer", 1080, 1920, 30, bpm_target=8)
        self.assertGreaterEqual(len(plan.beats), 1)
        self.assertEqual(plan.beats[0].kind, "top-card")
        # beats are within the timeline duration
        self.assertLessEqual(plan.beats[0].t_out, edl.timeline_duration + 0.01)

    def test_tiktok_makes_hook(self):
        edl = EDL(source="raw/x.mp4", fps=30, segments=[
            Segment(id="s000", src_in=0.0, src_out=3.0, text="Big hook line.",
                    word_start=0, word_end=3),
        ])
        t = Transcript(words=[Word("Big", 0.0, 0.4), Word("hook", 0.5, 0.9), Word("line.", 1.0, 2.9)])
        fmt = {"graphics": {"default_preset": "tiktok-raw-style", "layout": "hook-then-raw"}}
        plan = build_plan(edl, t, fmt, "short-tiktok", 1080, 1920, 30)
        self.assertEqual(plan.beats[0].kind, "hook-card")


if __name__ == "__main__":
    unittest.main()

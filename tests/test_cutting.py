import unittest

import tests._bootstrap  # noqa: F401
from scripts.lib.cutting import build_edl
from scripts.lib.transcript import Transcript, Word

CFG = {
    "min_gap": 0.35, "keep_pad": 0.08, "merge_gap": 0.12, "min_segment": 0.20,
    "drop_low_score": 0.35, "filler_words": ["like", "basically"], "aggressive_filler": False,
}


def make_transcript(pairs):
    return Transcript(words=[Word(text=t, start=s, end=e) for (t, s, e) in pairs])


class TestCutting(unittest.TestCase):
    def test_removes_hesitation_and_splits_on_silence(self):
        t = make_transcript([
            ("Hello", 0.0, 0.4), ("world", 0.45, 0.9),
            ("um", 1.0, 1.3),                       # hesitation -> removed
            ("this", 2.5, 2.8), ("is", 2.85, 3.0),  # 1.6s gap -> new span
            ("a", 3.05, 3.15), ("test", 3.2, 3.6),
        ])
        edl = build_edl(t, source="raw/x.mp4", cfg=CFG, fps=30)
        self.assertEqual(len(edl.segments), 2)
        joined = " ".join(s.text for s in edl.segments).lower()
        self.assertNotIn("um", joined.split())
        self.assertIn("hello", joined)
        self.assertIn("test", joined)
        # timeline shorter than source, and silence between spans removed
        self.assertLess(edl.timeline_duration, t.duration)

    def test_soft_filler_flagged_not_cut_by_default(self):
        t = make_transcript([
            ("This", 0.0, 0.3), ("is", 0.32, 0.45), ("like", 0.47, 0.7),
            ("really", 0.72, 1.1), ("cool", 1.12, 1.5),
        ])
        edl = build_edl(t, source="raw/x.mp4", cfg=CFG, fps=30)
        self.assertEqual(len(edl.segments), 1)
        self.assertIn("like", edl.segments[0].text.lower().split())
        self.assertTrue(any("filler" in s.note for s in edl.segments))

    def test_aggressive_cuts_soft_filler(self):
        t = make_transcript([
            ("This", 0.0, 0.3), ("is", 0.32, 0.45),
            ("like", 1.2, 1.5),                       # isolated so removal is visible
            ("cool", 2.4, 2.8),
        ])
        cfg = {**CFG, "aggressive_filler": True}
        edl = build_edl(t, source="raw/x.mp4", cfg=cfg, fps=30)
        joined = " ".join(s.text for s in edl.segments).lower().split()
        self.assertNotIn("like", joined)

    def test_word_indices_preserved(self):
        t = make_transcript([("a", 0.0, 0.2), ("b", 0.25, 0.4), ("c", 0.45, 0.6)])
        edl = build_edl(t, source="raw/x.mp4", cfg=CFG, fps=30)
        seg = edl.segments[0]
        self.assertEqual(seg.word_start, 0)
        self.assertEqual(seg.word_end, 3)

    def test_excludes_drop_phrase(self):
        t = make_transcript([
            ("keep", 0.0, 0.3), ("this", 0.32, 0.5),
            ("bad", 2.0, 2.3), ("take", 2.32, 2.6),      # separate span (gap)
            ("keep", 4.0, 4.3), ("that", 4.32, 4.6),     # separate span
        ])
        edl = build_edl(t, source="raw/x.mp4", cfg=CFG, fps=30, excludes=["bad take"])
        joined = " ".join(s.text for s in edl.segments).lower()
        self.assertNotIn("bad take", joined)
        self.assertIn("keep this", joined)
        rep = edl.meta["excludes"]
        self.assertTrue(rep[0]["matched"])
        self.assertEqual(rep[0]["removed"], 2)

    def test_excludes_time_range(self):
        t = make_transcript([("a", 0.0, 0.3), ("b", 2.0, 2.3), ("c", 4.0, 4.3)])
        edl = build_edl(t, source="raw/x.mp4", cfg=CFG, fps=30,
                        excludes=[{"start": 1.5, "end": 2.5}])
        joined = " ".join(s.text for s in edl.segments).lower().split()
        self.assertNotIn("b", joined)

    def test_midpoint_padding_no_overlap(self):
        # Two spans with a 0.5s gap; large keep_pad would overlap without clamping.
        t = make_transcript([("one", 0.0, 0.5), ("two", 1.0, 1.5)])
        cfg = {**CFG, "keep_pad": 0.4, "min_gap": 0.3}
        edl = build_edl(t, source="raw/x.mp4", cfg=cfg, fps=30)
        # merge_gap default 0.12; midpoints are 0.75/0.75 so spans stay separated by
        # the midpoint and never overlap.
        segs = sorted(edl.segments, key=lambda s: s.src_in)
        for a, b in zip(segs, segs[1:]):
            self.assertLessEqual(a.src_out, b.src_in + 1e-6)


if __name__ == "__main__":
    unittest.main()

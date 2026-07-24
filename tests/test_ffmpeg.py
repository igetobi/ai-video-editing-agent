import unittest

import tests._bootstrap  # noqa: F401
from scripts.lib import ffmpeg


class TestFfmpegCommands(unittest.TestCase):
    def test_trim_concat_builds_concat(self):
        cmd = ffmpeg.trim_concat("src.mp4", [(0.0, 1.0), (2.0, 3.0)], "out.mp4", 30, has_audio=True)
        s = " ".join(cmd)
        self.assertIn("trim=start=0.000:end=1.000", s)
        self.assertIn("atrim=start=2.000:end=3.000", s)
        self.assertIn("concat=n=2:v=1:a=1", s)

    def test_trim_concat_no_audio(self):
        cmd = ffmpeg.trim_concat("src.mp4", [(0.0, 1.0)], "out.mp4", 30, has_audio=False)
        s = " ".join(cmd)
        self.assertIn("concat=n=1:v=1:a=0", s)
        self.assertNotIn("atrim", s)

    def test_smooth_builds_xfade_chain(self):
        cmd = ffmpeg.trim_concat_smooth("src.mp4", [(0.0, 2.0), (5.0, 7.0), (9.0, 11.0)], "out.mp4", 30, transition=0.13)
        s = " ".join(cmd)
        self.assertIn("xfade=transition=fade", s)
        self.assertIn("acrossfade=d=", s)
        # two joins for three spans
        self.assertEqual(s.count("xfade=transition=fade"), 2)

    def test_smooth_transition_clamped_to_short_segment(self):
        # A 0.1s segment forces the transition below the 0.13 base (0.45*0.1=0.045).
        cmd = ffmpeg.trim_concat_smooth("src.mp4", [(0.0, 2.0), (5.0, 5.1)], "out.mp4", 30, transition=0.13)
        s = " ".join(cmd)
        self.assertIn("xfade=transition=fade:duration=0.045", s)

    def test_music_final_lufs_param(self):
        cmd = ffmpeg.add_music_ducked("v.mp4", "m.mp3", "o.mp4", music_gain_db=-23, final_lufs=-14)
        s = " ".join(cmd)
        self.assertIn("volume=-23dB", s)
        self.assertIn("loudnorm=I=-14", s)


if __name__ == "__main__":
    unittest.main()

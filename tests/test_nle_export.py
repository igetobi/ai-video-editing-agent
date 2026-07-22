import unittest

import tests._bootstrap  # noqa: F401
from scripts.lib.edl import EDL, Segment
from scripts.lib.nle_export import _tc, build_cmx3600_edl, build_fcpxml


def sample_edl():
    return EDL(source="raw/clip.mp4", fps=30, segments=[
        Segment(id="s000", src_in=2.0, src_out=4.0, text="hello"),
        Segment(id="s001", src_in=10.0, src_out=11.5, text="world"),
    ])


class TestNleExport(unittest.TestCase):
    def test_timecode(self):
        self.assertEqual(_tc(0.0, 30), "00:00:00:00")
        self.assertEqual(_tc(1.0, 30), "00:00:01:00")
        self.assertEqual(_tc(2.5, 30), "00:00:02:15")
        self.assertEqual(_tc(3661.0, 30), "01:01:01:00")

    def test_cmx3600(self):
        edl = sample_edl()
        text = build_cmx3600_edl(edl, title="myjob")
        self.assertIn("TITLE: myjob", text)
        self.assertIn("FCM: NON-DROP FRAME", text)
        self.assertIn("001", text)
        self.assertIn("002", text)
        self.assertIn("FROM CLIP NAME: clip.mp4", text)
        # record time of 2nd event starts where 1st ended (2.0s -> 00:00:02:00)
        self.assertIn("00:00:02:00", text)

    def test_fcpxml(self):
        edl = sample_edl()
        xml = build_fcpxml(edl, title="myjob", width=1920, height=1080)
        self.assertIn("<fcpxml version=\"1.9\">", xml)
        self.assertEqual(xml.count("<asset-clip"), 2)
        self.assertIn("width=\"1920\"", xml)
        self.assertIn("clip.mp4", xml)


if __name__ == "__main__":
    unittest.main()

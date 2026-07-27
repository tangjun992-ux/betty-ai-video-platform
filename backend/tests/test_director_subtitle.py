"""Director subtitle step bridges script/SRT to compose subtitle_track."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.director import _script_to_subtitle_track, _export_preset_from_params


def test_script_to_subtitle_track_splits_sentences():
    cues = _script_to_subtitle_track("第一句。第二句！Third.")
    assert len(cues) >= 2
    assert cues[0]["text"] == "第一句"
    assert cues[0]["start"] == 0.0
    assert cues[1]["start"] == 3.0


def test_export_preset_from_aspect_ratio():
    assert _export_preset_from_params({"aspect_ratio": "9:16"}) == "portrait_9_16"
    assert _export_preset_from_params({"export_preset": "square_1_1"}) == "square_1_1"

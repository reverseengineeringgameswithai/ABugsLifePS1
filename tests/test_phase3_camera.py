"""Phase-3 guard: the camera struct is a DERIVED OUTPUT.

This is the fact a mod most needs and least expects: the struct at 0x80095358
looks like camera state, but writing it does nothing lasting. If this test ever
fails, either the camera became authoritative (it didn't) or the experiment
regressed — and either way the mod contract must change."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CAM = json.loads((ROOT / "analysis" / "phase3_camera_record.json").read_text())
RECS = yaml.safe_load((ROOT / "config" / "record_types.yaml").read_text())["records"]


def test_neither_triple_is_authoritative():
    a = CAM["authority"]
    assert a["struct_is_derived"] is True
    assert a["write_camera_pos"]["held"] is False
    assert a["write_camera_target"]["held"] is False
    # both pokes must decay by a real margin, not a rounding wobble
    assert abs(a["write_camera_pos"]["drift_from_written"]) > 8000
    assert abs(a["write_camera_target"]["drift_from_written"]) > 8000


def test_follow_law_is_an_exponential_chase():
    f = CAM["follow_law"]
    assert f["samples"] >= 20
    assert 0.02 < f["gap_fraction_per_frame"] < 0.5, f


def test_camera_record_is_typed_with_both_triples():
    cam = next(r for r in RECS if r["id"] == "camera_record")
    names = {f["name"]: f["offset"] for f in cam["fields"]}
    assert names["camera_pos_x"] == 0x00
    assert names["camera_target_x"] == 0x0C
    # the lifetime statement must carry the derived-output warning, since that is
    # the whole safety story for this record
    assert "DERIVED OUTPUT" in cam["lifetime"]
    assert "0x8004DF18" in cam["lifetime"]


def test_fixtures_are_pinned():
    assert CAM["fixture_sha256"], "camera evidence pins no fixtures (DoF #1)"

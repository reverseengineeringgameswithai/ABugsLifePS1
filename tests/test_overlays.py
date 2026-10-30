"""Guard the overlay decompilation track (docs/EXECUTABLE_AND_OVERLAYS.md).

The overlay track (config/overlays.yml + tools/build_overlay.py) is SEPARATE from
the resident substrate: its own manifest, metric (analysis/overlay_decomp_progress
.json), and build/validate path against hash-pinned pristine staged blobs. CI-safe
legs check the manifest is well-formed and census-consistent; the byte-splat build
needs the owner's blobs and is local_media-gated.
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

MANIFEST = ROOT / "config" / "overlays.yml"
CENSUS = ROOT / "analysis" / "functions.json"


def _man():
    return yaml.safe_load(MANIFEST.read_text())


def _toint(v):
    return v if isinstance(v, int) else int(v, 16)


def test_overlay_manifest_well_formed():
    man = _man()
    assert _toint(man["region_a"]) == 0x800B39A0
    assert _toint(man["region_b"]) == 0x800B5788
    # every attempted entry maps to a real census overlay function of that stem
    fns = json.loads(CENSUS.read_text())["functions"]
    ov = {(r["overlay"], _toint(r["start"])): r for r in fns
          if r.get("space") == "overlay"}
    for name, o in (man.get("overlays") or {}).items():
        base = _toint(o["base"])
        for a in o.get("attempted") or []:
            start, end = _toint(a["start"]), _toint(a["end"])
            assert start < end, a
            assert start >= base, f"{name} {start:#x} below base {base:#x}"
            assert a["source"].startswith("src/overlays/") and a["source"].endswith(".c")
            rec = ov.get((name, start))
            assert rec is not None, f"{name} {start:#x} not a census overlay function"
            assert _toint(rec["end"]) == end, \
                f"{name} {start:#x} end {end:#x} != census {rec['end']}"


def test_overlay_track_is_separate_from_resident():
    """The overlay metric must not pollute the resident denominator."""
    man = _man()
    fns = json.loads(CENSUS.read_text())["functions"]
    overlay_starts = {_toint(a["start"])
                      for o in (man.get("overlays") or {}).values()
                      for a in (o.get("attempted") or [])}
    resident_starts = {_toint(r["start"]) for r in fns if r.get("space") == "resident"}
    assert not (overlay_starts & resident_starts), \
        "an overlay attempted entry collides with a resident function start"


@pytest.mark.local_media
def test_overlay_build_validates():
    """Every attempted overlay rebuild is identical to its pinned staged input."""
    import build_overlay
    seg = build_overlay._overlay_seg(_man())
    for name, ov in (_man().get("overlays") or {}).items():
        blob = ROOT / ov["blob"]
        if not blob.exists():
            pytest.fail(f"declared pristine staged overlay absent: {ov['blob']}")
        res = build_overlay.build_overlay(name, ov, seg)
        assert res["validated"], f"{name} rebuilt blob changed"
        assert res["matched_functions"] == len(ov.get("attempted") or [])

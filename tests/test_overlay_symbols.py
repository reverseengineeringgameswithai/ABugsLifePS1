"""Guards for the overlay name store (analysis/overlay_symbols.json + census wiring).

CI-safe: reads committed artifacts only. The regenerate==committed check needs the
owner's overlay blobs and is local_media-gated.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import validate_overlay_symbols as vos  # noqa: E402

STORE = ROOT / "analysis" / "overlay_symbols.json"
CENSUS = ROOT / "analysis" / "functions.json"


def test_store_valid():
    total, novl, errs = vos.check()
    assert not errs, errs[:10]
    assert total > 0 and novl > 0


def test_schema():
    doc = json.loads(STORE.read_text())
    assert doc["generated_by"] == "tools/apply_overlay_names.py"
    for ov, m in doc["overlays"].items():
        for a, e in m.items():
            assert re.fullmatch(r"0x[0-9a-f]{8}", a), a
            assert set(("name", "tier", "evidence")) <= set(e)


def test_census_uses_store():
    """Overlay records must carry the store's per-overlay names (no cross-overlay
    collision): the same address in two overlays can hold two different names."""
    doc = json.loads(STORE.read_text())
    fj = json.loads(CENSUS.read_text())
    census_names = {(f["overlay"], int(f["start"], 16)): f.get("name")
                    for f in fj["functions"] if f.get("space") == "overlay"}
    for ov, m in doc["overlays"].items():
        for a, e in m.items():
            key = (ov, int(a, 16))
            assert census_names.get(key) == e["name"], \
                f"census {key} = {census_names.get(key)!r} != store {e['name']!r}"


@pytest.mark.local_media
def test_regeneration_is_identical():
    before = STORE.read_bytes()
    proc = subprocess.run([sys.executable, "tools/function_census.py"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert STORE.read_bytes() == before

"""Guards for the C14 (dewdrop telescope) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_c14_telescope.md.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_c14_telescope.json"
TOOL = ROOT / "tools" / "phase4_c14_telescope_static.c"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_view_sequence_and_separate_producer():
    doc = load_artifact()
    seq = doc["VIEW_SEQUENCE_TRACED_2026-08-03"]
    assert "POLL-ONLY" in seq["scope"]
    assert "-1 per 2 frames" in seq["observed_lifecycle"]
    cam = seq["camera_behavior"]
    assert "PARKS" in cam
    assert "SEPARATE camera producer" in cam


def test_state_machine_documented_with_exact_constants():
    doc = load_artifact()
    sm = doc["STATE_MACHINE_DECODED_AND_C_PINNED_2026-08-03"]
    machine = sm["machine"]
    assert "252" in machine
    assert "-120" in machine
    assert "-10" in machine
    assert "0x800823A0" in machine
    assert "setpiece_spawn_manager 0x8004D698" in sm["owner"]


def test_e04_dual_attribution_resolved():
    doc = load_artifact()
    sm = doc["STATE_MACHINE_DECODED_AND_C_PINNED_2026-08-03"]
    assert "RESOLVED" in sm["e04_dual_attribution_RESOLVED"]
    assert "one owner" in sm["e04_dual_attribution_RESOLVED"].lower() or "ONE shared" in sm["e04_dual_attribution_RESOLVED"]


def test_c_tool_compiles_and_all_pins_verify():
    fd, out_path = tempfile.mkstemp()
    os.close(fd)
    try:
        build = subprocess.run(
            ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
             str(TOOL), "-o", out_path],
            capture_output=True, text=True,
        )
        assert build.returncode == 0, build.stderr
        run = subprocess.run([out_path, str(EXE)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        assert "27/27 OK" in run.stdout
    finally:
        os.remove(out_path)


def test_target_authoring_chain_documented():
    doc = load_artifact()
    tgt = doc["PREVIEW_SOURCE_AND_TARGET_AUTHORING_CLOSED_2026-08-03"]
    chain = tgt["the_chain"]
    assert "0x800823CC" in chain
    assert "0x80096DC8" in chain
    assert "0x80090BC0" in chain
    assert "ONE system" in chain
    layout = tgt["record_layout_decoded"]
    assert "0xC4" in layout
    assert "16 waypoints" in layout


def test_offline_live_cross_validation_is_exact():
    """The banked file coords must equal the banked runtime coords shifted <<5."""
    doc = load_artifact()
    tgt = doc["PREVIEW_SOURCE_AND_TARGET_AUTHORING_CLOSED_2026-08-03"]
    assert "(-2117,-5042,2678)" in tgt["offline_authored_coordinates_LEVEL01"]
    live = tgt["live_cross_validation_EXACT"]
    assert "(-67744,-161344,85696)" in live
    # the arithmetic the claim rests on
    assert (-2117 << 5, -5042 << 5, 2678 << 5) == (-67744, -161344, 85696)
    assert (-5576 << 5, -5620 << 5, -3772 << 5) == (-178432, -179840, -120704)
    assert "1-BASED" in live


def test_target_c_tool_compiles_and_pins_verify():
    tool = ROOT / "tools" / "phase4_c14_telescope_target.c"
    dat = ROOT / "REBUILD" / "files" / "LEVEL01" / "LEVEL.DAT"
    fd, out_path = tempfile.mkstemp()
    os.close(fd)
    try:
        build = subprocess.run(
            ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
             str(tool), "-o", out_path],
            capture_output=True, text=True,
        )
        assert build.returncode == 0, build.stderr
        run = subprocess.run([out_path, str(EXE), str(dat)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        assert "32/32 OK" in run.stdout
        # the authored coords must still be in the DAT exactly as banked
        assert "-2117" in run.stdout and "-5576" in run.stdout
    finally:
        os.remove(out_path)


def test_registry_row_updated():
    text = REGISTRY.read_text()
    start = text.index("  - id: C14_telescope")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "C14_telescope"
    assert row["status"] == "partial"
    joined = " ".join(row["bindings"])
    assert "VIEW SEQUENCE TRACED 2026-08-03" in joined
    assert "STATE MACHINE DECODED + C-PINNED 2026-08-03" in joined
    assert "PREVIEW SOURCE + TARGET AUTHORING CLOSED 2026-08-03" in joined
    assert "BOUNDED EXHAUSTED 2026-08-03" in row["next"]

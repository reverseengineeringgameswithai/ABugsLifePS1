"""Guards for the E01 (terrain visual geometry) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_e01_terrain_visual.md.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_e01_terrain_visual.json"
SURVEY = ROOT / "analysis" / "phase4_e01_node_survey.json"
TOOL = ROOT / "tools" / "phase4_e01_node_survey.py"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load(path):
    return json.loads(path.read_text())


def test_stale_binding_correction_documented():
    doc = load(ARTIFACT)
    synth = doc["RENDER_PATH_SYNTHESIS_2026-08-03"]
    corr = synth["stale_binding_corrected"]
    assert "FLICK.ALL" in corr
    assert "never drawn" in corr


def test_survey_self_check_matches_level01_ground_truth():
    doc = load(SURVEY)
    sc = doc["self_check"]
    assert sc["found"] is True
    assert sc["found_count"] == 42
    assert sc["level01_expected_node_base"] == "0x45f0"


def test_every_level_dir_has_a_substantial_primary_run():
    doc = load(SURVEY)
    by_dir = {}
    for lvl in doc["levels"]:
        d = lvl["file"].split("/")[2]
        for run in lvl["runs"]:
            by_dir.setdefault(d, []).append(run["count"])
    # LEVEL00..LEVEL10, all present, each with at least one >=30-record run
    # (LEVEL03 keeps its substantial geometry in its secondary LEVEL1.DAT).
    assert sorted(by_dir) == [f"LEVEL{n:02d}" for n in range(11)]
    for d, counts in by_dir.items():
        assert max(counts) >= 30, f"{d} has no substantial node-array candidate"


def test_primary_markers_are_in_the_c00x_family():
    doc = load(SURVEY)
    family = {"0x40000", "0x80040000", "0xc0040000", "0xc0060000",
              "0xc0070000", "0xc0080000", "0xc0090000"}
    # The per-level PRIMARY (largest) run's marker must be in the systematic family;
    # short noise runs elsewhere are allowed and separately flagged in the artifact.
    by_dir = {}
    for lvl in doc["levels"]:
        d = lvl["file"].split("/")[2]
        for run in lvl["runs"]:
            cur = by_dir.get(d)
            if cur is None or run["count"] > cur["count"]:
                by_dir[d] = run
    for d, run in by_dir.items():
        assert run["marker"] in family, f"{d} primary marker {run['marker']} outside family"


def test_survey_tool_regenerates_and_self_checks():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        out_path = tf.name
    try:
        result = subprocess.run(
            [sys.executable, str(TOOL), "--out", out_path],
            capture_output=True, text=True, cwd=ROOT, timeout=300,
        )
        assert result.returncode == 0, result.stderr
        fresh = json.loads(Path(out_path).read_text())
        banked = load(SURVEY)
        assert fresh["self_check"] == banked["self_check"]
        assert fresh["summary"] == banked["summary"], "survey drifted from the banked artifact -- regenerate or investigate"
    finally:
        Path(out_path).unlink(missing_ok=True)


def test_animation_model_resolved_with_flipbook_finding():
    doc = load(ARTIFACT)
    anim = doc["ANIMATION_MODEL_RESOLVED_2026-08-03"]
    assert "187/192" in anim["method_pass_2_level01_focused"]
    assert "(256,32)" in anim["method_pass_2_level01_focused"]
    assert "52 faces" in anim["offline_uv_join"]
    assert "@0x4c1a4" in anim["offline_uv_join"]
    assert "flipbook tile RE-UPLOAD" in anim["conclusion"]
    assert "NOT traced" in anim["hypothesis_flagged_not_traced"]


def test_registry_row_updated_with_correction_and_survey():
    text = REGISTRY.read_text()
    start = text.index("  - id: E01_terrain_visual")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "E01_terrain_visual"
    assert row["status"] == "partial"
    joined = " ".join(row["bindings"])
    assert "STALE HALF CORRECTED 2026-08-03" in joined
    assert "CAMPAIGN NODE SURVEY 2026-08-03" in joined
    assert "ANIMATION MODEL RESOLVED 2026-08-03" in joined
    assert "BOUNDED 2026-08-03" in row["next"]

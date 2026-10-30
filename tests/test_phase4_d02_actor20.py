"""Guards for the D02 (mover-VM / enemy actor +0x20 velocity_y) evidence.

See ObsidianVault/Experiments/EXP_2026-08-02_phase4_d02_actor20.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
FIRST_PASS = ROOT / "analysis" / "phase4_d02_actor20.json"
RUNTIME = ROOT / "analysis" / "phase4_d02_actor20_runtime.json"
DEEP_AUDIT = ROOT / "analysis" / "phase4_d02_actor20_deep_audit.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"
CANON = ROOT / "ObsidianVault" / "Canon" / "Memory" / "MEM_8009FD80_enemy_actor_pool.md"


def load(path):
    return json.loads(path.read_text())


def test_first_pass_falsifies_naive_frame_delta_only():
    doc = load(FIRST_PASS)
    assert doc["answer"].startswith("No:")
    rate = doc["aggregate"]["field_0x20_matches_y_moved_frames"]
    assert rate["matches"] == 61
    assert rate["total"] == 1431


def test_runtime_trace_fully_classified_zero_unclassified():
    doc = load(RUNTIME)
    trace = doc["trace"]
    assert trace["events"] == 1991
    assert trace["reads"] == 1178
    assert trace["writes"] == 813
    assert doc["instrumentation_control"]["ram_match"] is True
    assert doc["instrumentation_control"]["cycle_delta"] == 0


def test_deep_audit_confirms_velocity_y_not_frame_delta():
    doc = load(DEEP_AUDIT)
    assert doc["alternative_hypotheses"]["signed_velocity_y"] == "confirmed"
    assert doc["alternative_hypotheses"]["direct_frame_boundary_delta_y"].startswith("rejected")
    assert doc["runtime_accounting"]["writes"]["unclassified"] == 0
    assert doc["runtime_accounting"]["reads"]["unclassified"] == 0


def test_delay_slot_correction_is_explicit():
    doc = load(DEEP_AUDIT)
    corr = doc["delay_slot_correction"]
    assert corr["branch_pc"] == "0x8004D028"
    assert corr["store_pc"] == "0x8004D02C"
    assert "either branch outcome" in corr["correction"]


def test_static_tool_reproduces_documented_output():
    import subprocess
    import tempfile
    import os

    src = ROOT / "tools" / "phase4_d02_actor20_semantic_guard.c"
    fd, out_path = tempfile.mkstemp()
    os.close(fd)
    try:
        build = subprocess.run(
            ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
             str(src), "-o", out_path, "-lzstd", "-lcrypto"],
            capture_output=True, text=True,
        )
        assert build.returncode == 0, build.stderr
        run = subprocess.run([out_path], capture_output=True, text=True)
        assert run.returncode == 0
        result = json.loads(run.stdout)
        assert result["pristine_exe_sha256"] == "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"
        assert result["image_instruction_pins"] == 36
        assert result["writer_accounting"]["classified"] == 813
        assert result["writer_accounting"]["unclassified"] == 0
        assert result["alternative_hypotheses"]["signed_velocity_y"] == "confirmed"
    finally:
        os.remove(out_path)


def test_static_tool_rejects_a_non_pristine_image(tmp_path):
    import subprocess

    src = ROOT / "tools" / "phase4_d02_actor20_semantic_guard.c"
    tool = tmp_path / "actor20_guard"
    build = subprocess.run(
        ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
         str(src), "-o", str(tool), "-lzstd", "-lcrypto"],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    corrupt = tmp_path / "SCUS_942.88"
    image = bytearray((ROOT / "REBUILD" / "files" / "SCUS_942.88").read_bytes())
    image[0x800 + 0x8004BF14 - 0x80010000] ^= 0x01
    corrupt.write_bytes(image)
    run = subprocess.run([str(tool), str(corrupt)], capture_output=True, text=True)
    assert run.returncode != 0
    assert "pristine executable hash" in run.stderr


def test_canon_does_not_restate_the_superseded_unnamed_claim():
    """Presence-only guards missed both readings coexisting on the same page."""
    text = CANON.read_text()
    assert "remains intentionally unnamed" not in text
    assert "field remained unnamed is superseded" in text


def test_independent_verification_cites_cross_row_corroboration():
    doc = load(FIRST_PASS)
    verify = doc["INDEPENDENT_VERIFICATION_2026-08-03"]
    assert "B02_propeller_plant" in verify["cross_validation_from_a_different_row"]
    assert "-3328+256=-3072" in verify["fresh_live_resample"]


def test_independent_verification_flags_but_does_not_silently_fix_phase3_stale_claim():
    doc = load(FIRST_PASS)
    verify = doc["INDEPENDENT_VERIFICATION_2026-08-03"]
    note = verify["phase3_track_stale_claim_observed_not_fixed"]
    assert "phase3_contradictions.py" in note
    assert "not touched" in note.lower() or "NOT edited" in note


def test_registry_status_is_partial_with_bounded_next():
    text = REGISTRY.read_text()
    start = text.index("  - id: D02_mover_vm")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "D02_mover_vm"
    assert row["status"] == "partial"
    assert "ACTOR+0x20 FIELD CONFIRMED VELOCITY_Y" in " ".join(row["bindings"])
    assert "bounded 2026-08-02/03" in row["next"]

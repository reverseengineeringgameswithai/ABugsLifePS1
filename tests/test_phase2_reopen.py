"""Offline validation of the ninth-pass (reopen) artifacts: all-stage death
matrix, per-action negative controls, and the compare runner's report."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEATHS = json.loads((ROOT / "analysis" / "phase2_death_matrix.json").read_text())
NEGATIVES = json.loads((ROOT / "analysis" / "phase2_negative_controls.json").read_text())
COMPARE = json.loads((ROOT / "analysis" / "phase2_compare_report.json").read_text())


def test_death_matrix_every_stage_accounted():
    m = DEATHS["matrix"]
    assert len(m) == 16
    for lbl, e in m.items():
        assert e.get("death_observed") is not None, lbl
        if e["death_observed"]:
            assert e["law_lives_minus_1"] is True, lbl
            assert e["law_respawn_hp_4"] is True, lbl
            assert e["law_same_scene"] is True, lbl
        else:
            assert "note" in e and e["records_tried"] >= 1 or \
                e["records_available"] == 0, lbl
    # The strict-pristine in-level Training replacement contains a hostile
    # roster, so the respawn law now reproduces on 15/16 stages. Bug Bar remains
    # the bounded contact negative and its natural game-over is covered by soak.
    assert DEATHS["stages_with_death_observed"] == 15
    assert "method_caveats" in DEATHS


def test_negative_controls_all_pass():
    assert NEGATIVES["all_pass"] is True
    assert set(NEGATIVES["controls"]) == {
        "no_input_idle", "walk_no_square_no_carry",
        "single_jump_no_slide_states", "triangle_no_carry_no_color_change",
        "no_start_no_pause"}
    # non-vacuous premises (review fix): the jump control saw the airborne state
    assert NEGATIVES["controls"]["single_jump_no_slide_states"]["jump_state_observed"] is True
    for name, ctl in NEGATIVES["controls"].items():
        assert ctl["passes"] is True, name


def test_compare_report_pass_on_pristine():
    assert COMPARE["verdict"] == "PASS"
    assert COMPARE["mismatch_count"] == 0
    # The replacement Training anchor has ten stable fields rather than the
    # contaminated fixture's fifteen, so the honest low-level total is 696.
    assert COMPARE["checked"] == {
        "anchors": 42, "movies": 16, "comparisons": 696}
    assert len(COMPARE["state_inspections"]) == 42
    assert COMPARE["mounted_media_verification"]["pristine_verified"] is True
    assert COMPARE["media"]["serial"] == "SCUS-94288"


def test_spu_pitch_mutation_isolated():
    SPU = json.loads((ROOT / "analysis" / "phase2_spu_pitch_mutation.json").read_text())
    assert SPU["verdict"] == "DETECTED"
    assert SPU["isolated_to_spu_check"] is True
    assert SPU["checks_fired"] == ["mid_spu_voices"]


def test_negative_coverage_map_is_derived_and_honest():
    """The map must be DERIVED from the registry (every section-A core row
    present) and every verdict must be COMPUTED from evidence-artifact content
    (file+path+predicate checks), not declared. Two prior failures guard this:
    the hand-authored map omitted five actions; the first derived map still
    hand-declared verdicts with a hardcoded empty gap list."""
    import subprocess
    import sys as _sys

    import yaml as _yaml

    proc = subprocess.run([_sys.executable, "tools/phase2_coverage_map.py"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode in (0, 1), proc.stderr      # 1 == gaps remain (honest)
    COV = json.loads((ROOT / "analysis" / "phase2_negative_coverage_map.json").read_text())
    rows = _yaml.safe_load((ROOT / "analysis" / "mechanics_baseline.yaml").read_text())["rows"]
    core = [r["id"] for r in rows if r["section"] == "A"]
    assert sorted(COV["rows"]) == sorted(core), "map omits core-action rows"
    for rid, e in COV["rows"].items():
        # a covered verdict must be backed by evaluated checks, all OK
        if e["covered"]:
            assert e["evidence_checks"] and all(
                c.endswith("OK") for c in e["evidence_checks"]), rid
        else:
            assert any(g["row"] == rid for g in COV["gaps"]), rid
    # the gate flag must reflect reality, not aspiration
    assert COV["gate_bullet_3_met"] == (not COV["gaps"])
    # independent spot-verification: recompute one check straight from the
    # artifact and require agreement with the map's verdict for that row
    seeds = json.loads((ROOT / "analysis" / "phase2_seed_action_controls.json").read_text())
    a16_ok = (seeds["controls"]["A16_swinging"]["grab"]["positive"]["sustained_attach"]
              is True)
    assert COV["rows"]["A16_swinging"]["covered"] == (
        a16_ok and seeds["controls"]["A16_swinging"]["passes"] is True)


def test_movie_baseline_pristine_guarded():
    MB = json.loads((ROOT / "analysis" / "phase2_movie_baseline.json").read_text())
    assert MB["media"]["sha1"] == "0bc1a29748d4bd608d076495d085e825574880d1"
    assert MB["media"]["serial"] == "SCUS-94288"
    assert len(MB["movie_fixture_sha256"]) == 16


def test_capacity_hang_proof():
    HANG = json.loads((ROOT / "analysis" / "phase2_capacity_hang_proof.json").read_text())
    assert HANG["hang_confirmed"] is True
    assert HANG["free_slots_call"]["ok"] is True
    assert "Timed out" in HANG["all_occupied_call"]["error"]


def test_mutation_test_detects_known_bad_build():
    MUT = json.loads((ROOT / "analysis" / "phase2_mutation_test.json").read_text())
    assert MUT["verdict"] == "FAIL"          # the runner MUST fail on ALLMODS
    kinds = {m["what"] for m in MUT["mismatches"]}
    # every claimed regression-detector class fires on the known-bad build
    assert "mid_frame_sha256" in kinds       # visual (terrain/signs)
    assert "mid_spu_voices" in kinds         # audio incl. voice pitch
    assert "mid_pool_sha256" in kinds        # pool/pickup contents
    assert any(k.startswith("end:") for k in kinds)   # collected counters
    assert "entry_scene" in kinds            # scene flow

"""Offline validation of the closure pass: paired behavioral action controls,
results-lane baselines, and the regenerable standalone proofs."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BEHAVIOR = json.loads((ROOT / "analysis" / "phase2_action_behavior.json").read_text())
RESULTS = json.loads((ROOT / "analysis" / "phase2_results_baseline.json").read_text())
HANG = json.loads((ROOT / "analysis" / "phase2_capacity_hang_proof.json").read_text())
SPU = json.loads((ROOT / "analysis" / "phase2_spu_pitch_mutation.json").read_text())

PRISTINE_SHA1 = "0bc1a29748d4bd608d076495d085e825574880d1"


def test_behavioral_controls_measure_outcomes():
    assert BEHAVIOR["all_pass"] is True
    ctl = BEHAVIOR["controls"]

    # camera: the CAMERA struct MOVES under L1 and is static under no input
    cam = ctl["camera"]
    assert cam["l1_changes_camera"] is True
    assert cam["negative_control_camera_static"] is True
    assert cam["r1_changes_camera_differently_than_move_only"] is True

    # status: Select produces a DIFFERENT frame than the identical no-Select window
    st = ctl["status"]
    assert st["select_produces_different_frame"] is True
    assert st["panel_frame"] != st["control_frame"]

    # KICK: real positive/negative control on the kick timer 0x800A657A
    # (branch 0x80048F4C writes -16 when L2|R2 is held and Square is FRESH-pressed)
    k = ctl["kick"]
    assert k["l2_kick_fires"] is True
    assert k["r2_kick_fires"] is True
    assert k["square_alone_no_kick"] is True    # negative: throw, not kick
    assert k["no_input_no_kick"] is True        # negative: nothing
    assert k["kick_timer_start"] == -16
    assert "0x800A657A" in k["observable"]


def test_results_lane_baselined_and_pristine_guarded():
    assert RESULTS["media"]["sha1"] == PRISTINE_SHA1
    anchors = RESULTS["anchors"]
    assert len(anchors) >= 20
    roles = {a["role"] for a in anchors.values()}
    assert "lifecycle_completion" in roles      # results screens
    assert "objective_progress" in roles        # token/piece progression
    for lbl, a in anchors.items():
        assert len(a["frame_sha256"]) == 64, lbl
        assert a["typed"], lbl
    # distinct results screens must present distinct frames
    hashes = [a["frame_sha256"] for a in anchors.values()]
    assert len(set(hashes)) == len(hashes)


def test_proofs_are_regenerable_by_committed_tooling():
    for doc in (HANG, SPU):
        assert "tools/phase2_proofs.py" in doc["_comment"]
    assert HANG["hang_confirmed"] is True
    assert HANG["free_slots_call"]["ok"] is True
    assert "Timed out" in HANG["all_occupied_call"]["error"]
    assert SPU["verdict"] == "DETECTED"
    assert SPU["isolated_to_spu_check"] is True


FINAL = json.loads((ROOT / "analysis" / "phase2_final_action_pairs.json").read_text())
SEEDS = json.loads((ROOT / "analysis" / "phase2_seed_action_controls.json").read_text())
SPIN = json.loads((ROOT / "analysis" / "phase2_spin_disproof.json").read_text())


def test_final_action_pairs():
    assert FINAL["all_pass"] is True
    a14 = FINAL["controls"]["A14_plant_seed"]
    assert len(a14["creations"]) == 4
    assert sorted(a14["creation_types"]) == [6, 7, 7, 7]
    assert a14["all_creations_follow_cross_press"] is True
    a15 = FINAL["controls"]["A15_uproot_plant"]
    assert len(a15["teardowns"]) == 4
    assert a15["all_teardowns_follow_square_press"] is True
    assert a15["seed_raised_law"] is True and a15["seed_return_law"] is True
    assert a15["seed_raised_offset"] == 20480
    a11 = FINAL["controls"]["A11_seed_as_weapon"]
    pos, neg = a11["causal"]["positive"], a11["causal"]["negative_no_press"]
    assert pos["carry_broken"] and pos["knockback_write"] == -20
    # the narrative claims are MEASURED, not asserted (review cleanup):
    assert pos["seed_lands_on_hit_frame"] is True
    assert 0.3 <= pos["measured_decay_per_frame"] <= 0.7
    assert pos["enemy_removed_from_live_table"] is True
    assert not neg["carry_broken"] and neg["hit_frame"] is None
    assert neg["final_h6c"] == 0
    assert a11["replay_observable"]["enemy_slots_changed_across_drop"]
    # fixtures are hash-pinned
    assert all(len(v) == 64 for v in a14["fixture_sha256"].values())
    assert all(len(v) == 64 for v in a11["fixture_sha256"].values())


def test_seed_family_controls():
    assert SEEDS["all_pass"] is True
    for k in ("A12_seed_color_change", "A13_cycle_plant_output",
              "A10_handstand_negative", "A16_swinging"):
        assert SEEDS["controls"][k]["passes"] is True, k
    a16 = SEEDS["controls"]["A16_swinging"]
    # same-anchor action pairs (review: anchor-vs-anchor comparison retired)
    assert a16["grab"]["positive"]["sustained_attach"] is True
    assert a16["grab"]["negative_no_input"]["sustained_attach"] is False
    assert a16["release"]["positive"]["left_state5"] is True
    assert a16["release"]["positive"]["landed_grounded"] is True
    assert a16["release"]["negative_idle"]["left_state5"] is False


@pytest.mark.local_media
def test_spin_negative_is_reproducible_and_bounded():
    import subprocess
    import sys as _sys
    before = json.dumps(SPIN, sort_keys=True)
    proc = subprocess.run([_sys.executable, "tools/phase2_spin_disproof.py"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    after_doc = json.loads((ROOT / "analysis/phase2_spin_disproof.json").read_text())
    assert before == json.dumps(after_doc, sort_keys=True)
    assert after_doc["direct_clustered_direction_recognizer_found"] is False
    assert after_doc["classification"] == "documented_external_lead"
    assert after_doc["not_proven"], "bounded negative must retain its exclusions"
    assert len(after_doc["clusters"]) >= 4


def test_platform_gotcha_uses_raw_ab_observables():
    gotcha = json.loads((ROOT / "analysis/phase2_platform_gotchas.json").read_text())
    ab = gotcha["execTrace_movie_desynchronization"]
    assert ab["poll_only_a"] == ab["poll_only_b"]
    assert ab["poll_only_a"]["slot0_type"] == 7
    assert ab["poll_only_a"]["plant_cursor"] == 1
    assert ab["watch_armed"]["slot0_type"] == 0
    assert ab["watch_armed"]["plant_cursor"] == 0
    assert ab["poll_only_a"]["plant_table_sha256"] != \
        ab["watch_armed"]["plant_table_sha256"]
    # Do not allow the high-level boolean alone to carry this finding.
    assert ab["confirmed"] is True
    assert gotcha["non_regenerable_residuals"]


def test_compare_movie_lane_rejects_unmatched_profile(tmp_path):
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "tools"))
    import phase2_compare
    try:
        phase2_compare.validate_repro_config(tmp_path)
    except ValueError as exc:
        assert "settings" in str(exc)
    else:
        raise AssertionError("blank generic config was accepted for from-boot movies")

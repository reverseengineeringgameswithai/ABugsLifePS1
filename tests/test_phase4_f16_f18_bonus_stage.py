#!/usr/bin/env python3
"""Guards for Phase 4 F16/F17/F18 -- the bonus stage's rules and reward.

Three rows, one shared mechanism. These guards exist to stop the shared answer
decaying back into three vague ones, and to keep the two things that were WRONG on
the first pass from being re-introduced:

  * the completion predicate is a SHIFTED squared distance against a threshold of
    1600, and it is gated by a SECOND distance test at 359,999 on a different
    reference point. A description that mentions only the 1600 test is incomplete.
  * the reward is indexed by COMPLETION ORDER, not by which challenge was solved.

Static pins live in tools/phase4_f16_f18_bonus_stage.c (82 of them, -Werror); these
guard the banked artifact, the rows and the Canon page.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "analysis/phase4_f16_f18_bonus_stage.json"
CANON = ROOT / "ObsidianVault/Canon/Systems/SYS_bonus_stage.md"
ORDINAL_RESIDENT = ROOT / "analysis/phase4_bonus_ordinal_resident_census.json"
ORDINAL_OVERLAYS = ROOT / "analysis/phase4_bonus_ordinal_overlay_census.json"
TOOL_C = ROOT / "tools/phase4_f16_f18_bonus_stage.c"
TOOL_PY = ROOT / "tools/phase4_f16_f18_bonus_runtime.py"
EXP = ROOT / "ObsidianVault/Experiments/EXP_2026-08-04_phase4_f16_f18_bonus_stage.md"
ROWS = ("F16_bonus1_spiders", "F17_bonus2_mushrooms", "F18_bonus3_grasshoppers")


def rows():
    d = yaml.safe_load((ROOT / "analysis/mechanics_baseline.yaml").read_text(
        encoding="utf-8"))
    for v in d.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            return {x["id"]: x for x in v}
    raise AssertionError("no row list in mechanics_baseline.yaml")


@pytest.fixture(scope="module")
def art():
    return json.loads(ART.read_text())


# ------------------------------------------------------------------ artifact --

def test_artifact_exists_and_names_all_three_rows(art):
    assert set(art["rows"]) == set(ROWS)


def test_the_stage_was_actually_entered(art):
    assert art["entered_bonus_scene_at_frame"] is not None
    assert art["overlay_resident_at_frame"] is not None
    assert art["arrival"]["scene"] == 0x10


def test_load_base_was_measured_not_assumed(art):
    """The blob was LOCATED in RAM by its unique data tail. A first attempt signed on
    the function prologue and matched 0x38 off, because LEVEL06/LEVEL.BIN opens
    identically -- so 'measured' has to mean uniquely measured."""
    assert art["measured_load_base"] == "0x800B39A0"
    assert art["measured_base_matches_static"] is True


def test_live_overlay_matches_the_disc_blob(art):
    assert art["target_table_matches_disc"] is True
    assert art["descriptor_slot_50_is_own_token"] is True
    assert art["descriptor_slot_50"] == "0x800B3F78"


def test_completion_fired_inside_the_1600_radius(art):
    f = art["natural_fire"]
    assert f is not None, "the fixture never completed the stage"
    assert f["d2_at_fire"] < 1600
    assert f["d2_frame_before"] >= 1600, "the boundary must be crossed, not straddled"


def test_the_negative_side_of_the_boundary_was_measured(art):
    """A predicate confirmed only where it fires is half-tested."""
    n = art["negative_control"]
    assert n["frames_stepped_in_stage"] >= 100
    assert n["min_d2_before_firing"] >= 1600
    assert n["frames_inside_1600_that_did_NOT_fire"] == 0
    assert n["violations"] == []


def test_the_coarse_gate_is_real_and_was_observed(art):
    """The second distance test is not a rendering optimisation: the branch it takes
    skips the completion store too. It must be shown to actually fire, or it is just
    an unverified line in a listing."""
    n = art["negative_control"]
    assert n["frames_where_coarse_gate_blocked"] > 0
    assert n["max_coarse2_seen"] > 359999


def test_variant_cull_matched_the_static_prediction(art):
    assert art["variant_in_play"] == 0
    assert art["cull_matches_prediction"] is True
    assert art["actors_culled"] == list(range(12, 33))


def test_reward_commits_flags_and_advances_the_ordinal(art):
    before, after = art["pay_before"], art["pay_after"]
    assert before["flags"] == 0x02 and after["flags"] == 0x22, "(flags & 0x0F) * 17"
    assert after["ordinal"] == before["ordinal"] + 1
    assert art["scene_after_bonus"] == 0


def test_reward_pays_nothing_from_the_player_state_block(art):
    assert art["player_state_changed_by_reward"] == []
    for k in ("health", "lives", "power", "berry_idx", "invuln"):
        assert art["pay_before"][k] == art["pay_after"][k]


def test_fixture_is_declared_poll_only(art):
    """A v3 movie can never be traced. If someone later swaps in an Interpreter
    recording this string must change with it, deliberately."""
    assert "v3" in art["movie_format"] and "POLL ONLY" in art["movie_format"]


# ---------------------------------------------------------------- static tool --

def test_static_tool_builds_and_every_pin_holds(tmp_path):
    exe = tmp_path / "f16f18"
    subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-o", str(exe), str(TOOL_C)], check=True, cwd=ROOT)
    r = subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:]
    assert "0 failed" in r.stdout
    assert "every pin holds against the pristine image" in r.stdout


def test_static_tool_partitions_without_claiming_cfg_closure(tmp_path):
    exe = tmp_path / "f16f18"
    subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-o", str(exe), str(TOOL_C)], check=True, cwd=ROOT)
    r = subprocess.run([str(exe), "--accounting"], cwd=ROOT, capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout[-2000:]
    assert "the three structural regions sum to the whole file" in r.stdout
    assert "no resolved direct branch or call" in r.stdout
    assert "accounting is exhaustive" not in r.stdout
    assert "0 failed" in r.stdout


def test_base_derivation_is_not_hardcoded_prose():
    src = TOOL_C.read_text()
    assert "derive_base" in src
    assert "exactly one j/jal targets inside" in src


# ---------------------------------------------------------------------- rows --

@pytest.mark.parametrize("rid", ROWS)
def test_row_no_longer_lists_the_bonus_stage_as_missing(rid):
    r = rows()[rid]
    assert "Bonus stage rules/reward" not in (r.get("missing") or "")


@pytest.mark.parametrize("rid", ROWS)
def test_row_cites_the_shared_evidence(rid):
    b = " ".join(rows()[rid]["bindings"])
    assert "SYS_bonus_stage" in b or "0x800B39A0" in b
    assert "1600" in b


@pytest.mark.parametrize("rid", ROWS)
def test_row_records_that_the_stage_is_shared_not_per_challenge(rid):
    """The structural finding is the one most likely to be lost in a summary: the
    three rows do NOT have three bonus stages."""
    blob = json.dumps(rows()[rid])
    assert "ordinal" in blob
    assert "42" in blob


@pytest.mark.parametrize("rid", ROWS)
def test_row_still_flags_the_unobserved_variants(rid):
    """Variants 1 and 2 are pinned in the image but were never seen running. That
    limit must survive in the row, not only in the experiment note."""
    blob = json.dumps(rows()[rid]).lower()
    assert "variant" in blob


# --------------------------------------------------------------------- canon --

def test_canon_page_exists_and_states_the_predicate():
    t = flat(CANON)
    assert "1600" in t and "359,999" in t
    assert "0x800823A0" in t and "0x80082470" in t
    assert "0x8009B88A" in t


def test_bonus_ordinal_image_claim_matches_general_censuses():
    resident = json.loads(ORDINAL_RESIDENT.read_text())
    overlays = json.loads(ORDINAL_OVERLAYS.read_text())
    assert [(x["pc"], x["kind"]) for x in resident["readers"] + resident["writers"]] == [
        ("0x8004FFAC", "read"), ("0x8004FFD0", "write"),
    ]
    bonus = next(x for x in overlays["overlays"] if x["overlay"] == "LEVEL06_LEVEL1")
    assert [(x["pc"], x["kind"]) for x in bonus["hits"]] == [
        ("0x800B3B38", "read"), ("0x800B3C9C", "read"),
    ]
    assert bonus["unresolved_base_accesses"] == 129
    assert sum(x["unresolved_base_accesses"] for x in overlays["overlays"]) == 4967


def test_false_only_image_claim_stays_in_correction_history_only():
    canon = CANON.read_text()
    source = TOOL_C.read_text()
    assert "this blob is the\nonly image in the game that reads" not in canon
    assert "this is the ONLY image in the game that reads" not in source
    assert "was factually false because the resident EXE reads it" in flat(CANON)
    assert "only overlay with resolved direct" in source


def flat(path):
    """Markdown is hard-wrapped, so a phrase can straddle a newline. Guards should
    fail when the CLAIM disappears, not when someone re-flows a paragraph."""
    return " ".join(path.read_text().split())


def test_canon_records_the_fallthrough_so_nobody_fixes_it():
    t = flat(CANON)
    assert "not an else-branch" in t
    assert 'Do not "fix" the missing branch' in t


def test_canon_marks_variants_1_and_2_as_unobserved():
    assert "Only **variant 0** has been observed running" in flat(CANON)


def test_canon_scopes_negative_claims_to_the_evidence():
    text = CANON.read_text()
    t = flat(CANON)
    assert "decoded completion block has no timer, score, fail-state or enemy gate" in t
    assert "pointer-derived stores or callee effects" in t
    assert "There is no timer, no score, no fail state and no enemy requirement anywhere" not in text
    assert "**Nothing else is paid.**" not in text
    assert "No store in the whole bonus overlay" not in text


def test_static_tool_does_not_turn_a_fixed_form_scan_into_closure():
    src = TOOL_C.read_text()
    assert "no store in the whole bonus overlay reaches" not in src
    assert "the reward pays nothing but the movie" not in src
    assert "pointer-derived stores and callee effects remain outside its scope" in src


def test_retracted_bonus_negatives_are_not_live_in_the_evidence_chain():
    for path in (CANON, EXP, TOOL_PY):
        text = path.read_text()
        assert "There is no timer, no score, no fail state and no enemy requirement anywhere" not in text
        assert "It pays nothing else" not in text
        assert "Flik's position is read-only to the overlay" not in text
    assert "It also captures what the stage pays" not in TOOL_PY.read_text()


def test_structural_partition_is_not_described_as_complete_accounting():
    canon = CANON.read_text()
    exp = EXP.read_text()
    source = TOOL_C.read_text()
    assert "**accounted for completely**" not in canon
    assert "proves the split is exhaustive" not in exp
    assert "accounted for completely -- there is no fifth function" not in source
    assert "Indirect control flow and semantic reachability are not closed" in flat(CANON)


def test_bonus1_absolute_closure_is_not_live_in_the_experiment():
    exp = EXP.read_text()
    assert "**The domain is closed.**" not in exp
    assert "complete statement rather than a survey" not in exp
    assert "Resolved-site census, not domain closure" in exp


def test_experiment_note_records_the_first_pass_errors():
    t = flat(EXP)
    assert "What a first reading got wrong" in t
    assert "Read too early" in t
    assert "signature that wasn't unique" in t


def test_runtime_tool_refuses_silent_zeros():
    """scatterRead returns value 0 with valid=false for an unreadable item. Treating
    that as data is exactly how the first pass produced a plausible wrong number."""
    src = TOOL_PY.read_text()
    assert "valid" in src and "refusing" in src

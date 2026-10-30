import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_caller_domain as pilot  # noqa: E402


def retained():
    return json.loads(pilot.OUTPUT.read_text())


def test_frozen_universe_precedes_outcomes_and_is_exact():
    raw, ids = pilot._verify_freeze_note()
    assert raw
    assert ids == list(pilot.PILOT_IDS)
    assert len(ids) == len(set(ids)) == 20
    assert len(pilot.STACK_IDS) == 5
    assert len(pilot.RETURN_IDS) == 5
    assert len(pilot.INDEX_IDS) == 10


def test_pilot_receipt_is_reproducible():
    proc = subprocess.run(
        ["python3", str(pilot.ROOT / "tools/phase4_caller_domain.py"), "--check"],
        cwd=pilot.ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_independent_implementation_agrees_on_all_20():
    doc = retained()
    check = doc["independent_crosscheck"]
    assert check["all_20_agree"] is True
    assert check["disagreements"] == []
    assert check["sample_site_ids"] == list(pilot.PILOT_IDS)
    assert all(row["independent_crosscheck"]["agrees"] for row in doc["sites"])


def test_no_go_is_derived_without_open_count_inflation():
    doc = retained()
    decision = doc["decision"]
    assert decision["verdict"] == "NO-GO"
    assert decision["decided_site_count"] == 0
    assert decision["reasons"] == ["decided_site_count_below_3"]
    assert decision["open_poison_site_count"] == 10
    assert decision["open_poison_comparison"] == "strictly_greater_than_10"
    assert decision["full_pass_authorized"] is False

    walls = doc["stage_b_sample_domains"]["wall_site_sets"]
    assert set(walls["open_caller_set_poison"]) == (
        set(pilot.STACK_IDS) | {site for site in pilot.INDEX_IDS if "0x8005C5" in site}
    )
    local = set(walls["local_definition_replaces_argument_register"])
    local |= set(walls["local_frame_slot_not_stack_argument"])
    local |= set(walls["local_signed_load_not_caller_argument"])
    assert local == set(pilot.INDEX_IDS[:5])


def test_call_delay_slots_are_not_return_values():
    rows = {row["id"]: row for row in retained()["sites"]}
    for site_id, pc in ((pilot.RETURN_IDS[0], "0x800b41a8"),
                        (pilot.RETURN_IDS[2], "0x800b4770")):
        row = rows[site_id]
        assert row["wall"] == "delay_slot_pre_call_value_not_return_domain"
        assert row["breaking_instruction"] == {
            "pc": pc,
            "word": "0x0c013043",
        }


def test_capsule_gate_does_not_call_zero_samples_clean():
    gate = retained()["capsule_crosscheck"]
    assert gate["capsule_universe"] == 50
    assert gate["site_time_observations"] == 0
    assert gate["clean_for_go"] is False
    assert gate["soundness_violation"] is False


def test_f01_protected_state_and_no_stage_c_movement():
    doc = retained()
    assert doc["protected_state"] == {
        "dimension_promoted": False,
        "f01_status": "partial",
        "item2_ready_for_review": False,
        "item_2": "not_met",
        "mechanics_baseline_modified": False,
        "movie_or_fixture_modified": False,
        "review_blockers": ["IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"],
    }
    stage_c = doc["stage_c_not_run"]
    assert stage_c["old_pins_replaced"] == []
    for key in ("fixture_store_movement", "ledger_movement", "campaign_row_movement"):
        assert stage_c[key] == {"gained_ids": [], "lost_ids": []}

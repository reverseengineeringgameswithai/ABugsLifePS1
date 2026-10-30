"""Guards for the D01 (general enemy spawn/update) synthesis evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_d01_enemy_spawn_update.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d01_enemy_spawn_update.json"
CENSUS = ROOT / "analysis" / "phase1_kind_actor_census.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_scheduler_synthesis_cites_committed_owners():
    doc = load_artifact()
    synth = doc["SCHEDULER_AND_LIFECYCLE_SYNTHESIS_2026-08-03"]
    assert "0x8004A42C" in synth["pool_init"]
    assert "0x80049C30" in synth["program_selection"]
    assert "0x8004D224" in synth["per_frame_scheduler"]
    assert "0x80049C2C" in synth["respawn"]
    assert "FUNC_80046B20" in synth["quota_derivation"]


def test_pool_base_reconciliation_is_arithmetically_true():
    doc = load_artifact()
    rec = doc["POOL_BASE_RECONCILIATION_2026-08-03"]
    assert "0x8009FE04 = 0x8009FD80 + 0x84" in rec["observation"]
    assert 0x8009FD80 + 0x84 == 0x8009FE04
    assert 0x8009FD80 + 4 * 0x84 == 0x8009FF90
    assert "0x80090748" in rec["caveat"]


def test_roster_binds_seventeen_of_the_unknowns():
    doc = load_artifact()
    roster = doc["ID_ROSTER_RECONCILIATION_2026-08-03"]
    bound = roster["newly_bound_from_the_36_unknowns"]
    assert len(bound) == 17
    census = json.loads(CENSUS.read_text())
    unknown = set(census["actor_ids_unknown_role"])
    for id_str in bound:
        assert int(id_str) in unknown, f"id {id_str} was not in the census unknown list"


def test_remaining_nineteen_are_the_set_difference():
    doc = load_artifact()
    roster = doc["ID_ROSTER_RECONCILIATION_2026-08-03"]
    bound = {int(k) for k in roster["newly_bound_from_the_36_unknowns"]}
    census = json.loads(CENSUS.read_text())
    unknown = set(census["actor_ids_unknown_role"])
    remaining = sorted(unknown - bound)
    assert len(remaining) == 19
    assert remaining == [0, 1, 2, 3, 4, 5, 7, 8, 11, 20, 21, 23, 24, 25, 26, 27, 28, 32, 35]


def test_thud_is_outside_the_census_set():
    census = json.loads(CENSUS.read_text())
    assert 36 not in census["actor_ids_observed"]
    doc = load_artifact()
    assert "0x24" in doc["ID_ROSTER_RECONCILIATION_2026-08-03"]["bound_outside_the_census"]


def test_bird_type_word_provenance_history_preserved():
    doc = load_artifact()
    bird = doc["ID_ROSTER_RECONCILIATION_2026-08-03"]["newly_bound_from_the_36_unknowns"]["30"]
    assert "an inference" in bird
    assert "RESOLVED" in bird


def test_id11_characterized_as_flag_excluded_ambient():
    doc = load_artifact()
    id11 = doc["ID11_CHARACTERIZED_LIVE_2026-08-03"]
    result = id11["result"]
    assert "hp=1" in result
    assert "0x4030" in result
    assert "0x8007755C" in result
    interp = id11["interpretation"]
    assert "0x20" in interp
    assert "quota" in interp.lower()
    # The flag claim is arithmetically real: 0x4030 & 0x08A0 (C04 exclusion mask) != 0
    assert 0x4030 & 0x08A0 == 0x20


def test_bird_type_word_hedge_resolved_by_direct_read():
    doc = load_artifact()
    id11 = doc["ID11_CHARACTERIZED_LIVE_2026-08-03"]
    assert "0x1A1E" in id11["bird_type_word_hedge_resolved"]
    bird = doc["ID_ROSTER_RECONCILIATION_2026-08-03"]["newly_bound_from_the_36_unknowns"]["30"]
    assert "RESOLVED" in bird


def test_still_open_reflects_eighteen_remaining():
    doc = load_artifact()
    assert "18 of 36" in doc["STILL_OPEN"]


def test_registry_status_is_partial_with_bounded_next():
    text = REGISTRY.read_text()
    start = text.index("  - id: D01_enemy_spawn_update")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "D01_enemy_spawn_update"
    assert row["status"] == "partial"
    assert "SYNTHESIS 2026-08-03" in " ".join(row["bindings"])
    assert "ID11 CHARACTERIZED LIVE 2026-08-03" in " ".join(row["bindings"])
    assert "BOUNDED EXHAUSTED 2026-08-03" in row["next"]

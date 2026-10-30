"""Guards for the C04 (enemy success token / permanent elimination quota) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_c04_enemy_token.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_c04_enemy_token.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_writer_function_and_field_identity():
    doc = load_artifact()
    mech = doc["MECHANISM_CONFIRMED_LIVE_2026-08-03"]
    assert mech["writer_function"].startswith("FUNC_80046B20")
    assert "0x800A6500" in mech["reset"]
    assert "0x800A658E" in mech["reset"]


def test_scan_loop_describes_pool_and_exclusion_mask():
    doc = load_artifact()
    mech = doc["MECHANISM_CONFIRMED_LIVE_2026-08-03"]
    loop = mech["scan_loop"]
    assert "0x8009FD80" in loop
    assert "0x84" in loop
    assert "0x08A0" in loop


def test_live_write_events_show_incrementing_sequence():
    doc = load_artifact()
    mech = doc["MECHANISM_CONFIRMED_LIVE_2026-08-03"]
    events = mech["live_write_events"]
    assert "0x80046c64" in events
    assert "0->1->2->3->4" in events


def test_cross_level_check_shows_different_computed_totals():
    doc = load_artifact()
    mech = doc["MECHANISM_CONFIRMED_LIVE_2026-08-03"]
    cross = mech["cross_check_different_level"]
    assert "quota=4" in cross
    assert "quota=50" in cross


def test_exclusion_bit_0x0800_flagged_as_unconfirmed_hypothesis():
    doc = load_artifact()
    interp = doc["EXCLUSION_BITS_INTERPRETATION"]
    assert "hypothesis, not a claim" in interp["bit_0x0800_hypothesis_NOT_confirmed"]
    assert "D14" in interp["cross_reference"]


def test_token_grant_ties_quota_to_the_shared_goal_latch():
    doc = load_artifact()
    grant = doc["TOKEN_GRANT_CONFIRMED_LIVE_2026-08-03"]
    assert "0x800823A0" in grant["result"]
    assert "0x80082470" in grant["result"]
    assert "D19_molt" in grant["result"]
    assert "130337" in grant["result"]


def test_token_grant_causal_structure_not_just_correlation():
    doc = load_artifact()
    grant = doc["TOKEN_GRANT_CONFIRMED_LIVE_2026-08-03"]
    causal = grant["causal_structure_verified"]
    assert "unconditional" in causal.lower()
    assert "quota==1" in causal or "quota == 1" in causal or "against s2" in causal


def test_token_grant_honestly_flags_the_isolation_caveat():
    doc = load_artifact()
    grant = doc["TOKEN_GRANT_CONFIRMED_LIVE_2026-08-03"]
    caveat = grant["caveat_not_isolated_variable"]
    assert "not run this pass" in caveat or "not isolated" in caveat.lower() or "simultaneously" in caveat.lower()


def test_registry_status_is_partial_with_bounded_next():
    text = REGISTRY.read_text()
    start = text.index("  - id: C04_enemy_token")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "C04_enemy_token"
    assert row["status"] == "partial"
    assert "QUOTA CONSTRUCTION CONFIRMED LIVE 2026-08-03" in " ".join(row["bindings"])
    assert "0x80046c64" in " ".join(row["bindings"])
    assert "bounded 2026-08-03" in row["next"]

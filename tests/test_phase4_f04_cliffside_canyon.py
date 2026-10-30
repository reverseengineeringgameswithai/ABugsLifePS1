"""Guards for the F04 (Cliffside Canyon stage) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_f04_cliffside_canyon.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_f04_cliffside_canyon.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_status_reflects_triple_synthesis():
    doc = load_artifact()
    assert "triple-synthesis" in doc["status"].lower()
    assert "B03_dandelion_glide" in doc["status"]
    assert "D17_bird" in doc["status"]


def test_special_flight_cites_b03_mechanism():
    doc = load_artifact()
    flight = doc["SPECIAL_FLIGHT_SYNTHESIZED_FROM_B03_2026-08-03"]
    assert "0x8005C818" in flight["mechanism"]
    assert "30,720" in flight["mechanism"]
    assert "vy=-4096" in flight["mechanism"]


def test_special_flight_cites_propeller_interaction():
    doc = load_artifact()
    flight = doc["SPECIAL_FLIGHT_SYNTHESIZED_FROM_B03_2026-08-03"]
    propeller = flight["propeller_updraft_interaction"]
    assert "latch 11" in propeller
    assert "12=a separate" in propeller


def test_kill_zone_cites_d17_shared_actor():
    doc = load_artifact()
    kz = doc["KILL_ZONE_SYNTHESIZED_FROM_D17_2026-08-03"]
    identity = kz["identity"]
    assert "id=30" in identity
    assert "hp 101" in identity or "101" in identity
    assert "Birdnest" in identity


def test_kill_zone_mechanism_describes_dive_and_lives_decrement():
    doc = load_artifact()
    kz = doc["KILL_ZONE_SYNTHESIZED_FROM_D17_2026-08-03"]
    mech = kz["mechanism"]
    assert "1,365" in mech or "1365" in mech
    dmg = kz["damage_and_respawn_cycle"]
    assert "lives decrement" in dmg.lower()
    assert "health stays constant" in dmg.lower() or "constant at 4" in dmg.lower()


def test_kill_zone_inherits_unresolved_d17_residuals():
    doc = load_artifact()
    kz = doc["KILL_ZONE_SYNTHESIZED_FROM_D17_2026-08-03"]
    not_closed = kz["not_fully_closed_by_d17"]
    assert "FUNC_8004ABF4" in not_closed
    assert "0x10" in not_closed


def test_campaign_breadth_cites_d11_mite():
    doc = load_artifact()
    breadth = doc["CAMPAIGN_BREADTH_SYNTHESIZED_FROM_D11_2026-08-03"]
    assert "id=37" in breadth["result"]
    assert "canyon_bug" in breadth["result"]


def test_still_open_flags_stage_level_flow_as_unaddressed():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "level design/flow" in still_open.lower() or "level-design" in still_open.lower() or "level layout" in still_open.lower()


def test_registry_status_is_partial_not_unresolved():
    text = REGISTRY.read_text()
    start = text.index("  - id: F04_cliffside_canyon")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "status: partial" in block
    assert "status: unresolved" not in block
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "F04_cliffside_canyon"
    assert row["status"] == "partial"
    assert "0x8005C818" in " ".join(row["bindings"])
    assert "id=30" in " ".join(row["bindings"])


def test_registry_missing_field_flags_critical_path_gap():
    text = REGISTRY.read_text()
    start = text.index("  - id: F04_cliffside_canyon")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "critical path" in block.lower()
    assert "FUNC_8004ABF4" in block

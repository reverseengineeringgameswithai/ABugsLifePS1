import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d12_bounded_exhaustion.json"
GUARD = ROOT / "tools" / "phase4_d12_closure.c"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_d12_is_substantiated_partial_and_bounded_exhausted():
    doc = load_artifact()
    assert doc["row"] == "D12_centipedes_earthworms"
    assert doc["status"]["row"] == "substantiated_partial"
    assert doc["status"]["bounded_subproblem"] == "exhausted_move_on"
    assert doc["status"]["additional_interpreter_movie_required"] is False


def test_stale_strike_and_respawn_claims_are_explicitly_corrected():
    corrections = load_artifact()["corrections"]
    assert corrections["spawned_burst_damage"]["result"].startswith("Falsified")
    assert "0x8004A664" in corrections["respawn_caller"]["result"]
    assert "0x8004D3F0" in corrections["respawn_caller"]["result"]
    assert "camera-containment" in corrections["respawn_gate"]["result"]
    assert "+0x62" in corrections["respawn_timer"]["result"]
    assert "+0x4A" in corrections["respawn_timer"]["result"]


def test_mine_interaction_is_bounded_without_claiming_instant_kill():
    mine = load_artifact()["mine_interaction"]
    assert mine["blast_constructor"] == 56
    assert mine["damage_class"] == 0
    assert mine["worm_initial_local_hp"] == 8
    assert mine["single_blast_local_hp_result"] == 6
    assert mine["instant_kill"] is False


def test_c_guard_pins_all_four_closure_domains():
    source = GUARD.read_text()
    for token in (
        "0x800795c0",
        "0x800795d4",
        "0x800795e8",
        "0x8004d3f0",
        "0x8004d3bc",
        "0x8004d40c",
        "0x8007987c",
        "0x80058f08",
    ):
        assert token in source

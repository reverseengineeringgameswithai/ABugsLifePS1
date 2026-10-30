"""Guards for the D15 (daddy long legs) evidence.

See ObsidianVault/Experiments/EXP_2026-08-02_phase4_d15_daddy_long_legs.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d15_daddy_long_legs.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_identity_id17_is_daddy_long_legs():
    doc = load_artifact()
    identity = doc["IDENTITY_2026-08-02"]
    assert "id=17" in identity["result"]
    assert "huge_spider" in identity["result"]
    assert "huge_spider\" is daddy long legs" in identity["visual_confirmation"]
    assert "0x0b11" in identity["type_word_cross_check"]


def test_no_strike_mechanic_static():
    doc = load_artifact()
    finding = doc["NO_STRIKE_MECHANIC_STATIC_2026-08-02"]
    assert "0x80077674" in finding["method"]
    assert "no player_proximity opcode and no call_native" in finding["result"].lower() or \
        "NO player_proximity opcode and NO call_native" in finding["result"]
    assert "web projectile" in finding["result"].lower()


def test_combat_timeline():
    doc = load_artifact()
    combat = doc["COMBAT_AND_DEATH_2026-08-02"]
    assert "f286" in combat["timeline"]
    assert "f318" in combat["timeline"]
    assert "f328" in combat["timeline"]
    assert "f352" in combat["timeline"]
    assert "f400" in combat["timeline"]
    assert "hp 4->2" in combat["timeline"]
    assert "-2 per hit" in combat["damage_amount"]


def test_aggro_original_claim_marked_retracted():
    doc = load_artifact()
    aggro = doc["AGGRO_2026-08-02"]
    assert "0x4103" in aggro["result"]
    assert "RETRACTED" in aggro["conclusion_ORIGINAL_2026-08-02"]


def test_aggro_correction_documents_operator_pushback_and_followup():
    doc = load_artifact()
    correction = doc["AGGRO_CORRECTION_2026-08-02"]
    assert "surely it has aggro since it shoots a web" in correction["trigger"]
    assert "web_attack.sav" in correction["follow_up_attempt"]
    assert "scene_id=1" in correction["follow_up_attempt"]
    assert "id=14" in correction["follow_up_result_INCONCLUSIVE"]
    assert "daddylonglegs in ABL is fine" in correction["follow_up_result_INCONCLUSIVE"]
    assert "RETRACTED" in correction["net_effect_on_banked_claims"]


def test_web_attack_confirmed_live():
    doc = load_artifact()
    confirmed = doc["WEB_ATTACK_CONFIRMED_2026-08-02"]
    assert "f312" in confirmed["result"]
    assert "73286" in confirmed["result"]
    assert "f604" in confirmed["result"]
    assert "48405" in confirmed["result"]
    assert "f798" in confirmed["result"]
    assert "14245" in confirmed["result"]
    assert "RANGED ATTACK" in confirmed["result"]
    assert confirmed["conclusion"].startswith("CONFIRMED POSITIVE")
    assert "fully reverses the AGGRO_2026-08-02" in confirmed["conclusion"]


def test_web_attack_counterattack_and_death():
    doc = load_artifact()
    confirmed = doc["WEB_ATTACK_CONFIRMED_2026-08-02"]
    ca = confirmed["counterattack_and_death"]
    assert "f1280" in ca
    assert "f1340" in ca
    assert "f1390" in ca
    assert "hp 4->2" in ca
    assert "999" in ca


def test_still_open_no_longer_treats_web_attack_as_unconfirmed():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "the web attack itself" not in still_open
    assert "campaign breadth" in still_open.lower()
    assert "respawn" in still_open.lower()


def test_producer_chain_damage_side_closes_against_canon_code():
    doc = load_artifact()
    chain = doc["PRODUCER_CHAIN_TRACED_2026-08-02"]
    damage = chain["damage_side"]
    assert "0x8004a888" in damage["result"]
    assert "0x80058A48" in damage["result"]
    assert "FUNC_8004A700" in damage["result"]


def test_producer_chain_false_lead_ruled_out_not_silently_replaced():
    doc = load_artifact()
    chain = doc["PRODUCER_CHAIN_TRACED_2026-08-02"]
    false_lead = chain["spawn_side_FALSE_LEAD_RULED_OUT"]
    assert "RULED OUT" in false_lead["correction"]
    assert "action_id=1" in false_lead["correction"]
    assert "0x8005a0e0" in false_lead["correction"].lower() or "0x8005A0E0" in false_lead["correction"]


def test_producer_chain_real_spawn_caller_identified():
    doc = load_artifact()
    chain = doc["PRODUCER_CHAIN_TRACED_2026-08-02"]
    real = chain["real_spawn_caller_0x8004a2b0"]
    assert "0x8004a2b0" in real["method"].lower()
    assert "action_id 118" in real["result"] or "118" in real["result"]
    indirect = real["indirect_dispatch"]
    assert "aimed_object_spawn_sfx" in indirect
    assert "+0x7C" in indirect
    assert "mosquito_species_callback" in indirect


def test_dod_scorecard_present_and_notes_self_correction():
    doc = load_artifact()
    chain = doc["PRODUCER_CHAIN_TRACED_2026-08-02"]
    scorecard = chain["dod_scorecard_2026-08-02"]
    assert "MET" in scorecard
    assert "ADVANCED" in scorecard
    assert "DEFERRED" in scorecard
    assert "self-caught" in scorecard.lower() or "correction" in scorecard.lower()


def test_callback_confirmed_live_closes_the_hypothesis():
    doc = load_artifact()
    confirmed = doc["CALLBACK_CONFIRMED_LIVE_2026-08-03"]
    assert "0x800a0ae8" in confirmed["result"]
    assert "0x8004a2b0" in confirmed["result"].lower()
    assert "zero variation" in confirmed["result"]
    assert confirmed["conclusion"].startswith("CONFIRMED POSITIVE")


def test_still_open_no_longer_lists_the_callback_question():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "whether daddy-long-legs' own live actor record actually carries" not in still_open
    assert "CLOSED 2026-08-03" in still_open


def test_registry_missing_no_longer_lists_the_callback_as_open():
    text = REGISTRY.read_text()
    start = text.index("  - id: D15_daddy_long_legs")
    end = text.index("  - id: D16_thumper")
    block = text[start:end]
    assert "CALLBACK CONFIRMED LIVE 2026-08-03" in block
    assert "CLOSED 2026-08-03: the +0x7C=0x8004A2B0" in block


def test_registry_status_is_partial_not_solved():
    text = REGISTRY.read_text()
    start = text.index("  - id: D15_daddy_long_legs")
    end = text.index("  - id: D16_thumper")
    block = text[start:end]
    assert "status: partial" in block
    assert "status: solved" not in block
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "D15_daddy_long_legs"
    assert row["status"] == "partial"

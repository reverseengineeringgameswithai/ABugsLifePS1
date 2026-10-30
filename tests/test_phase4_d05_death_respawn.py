"""Guards for the D05 (enemy death/despawn/respawn) evidence, synthesized from D09/D12/D13.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_d05_death_respawn.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d05_death_respawn.json"
DONOR = ROOT / "analysis" / "phase4_d12_worm_id40.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_respawn_condition_requires_real_walk_away():
    doc = load_artifact()
    synth = doc["SYNTHESIZED_FROM_D09_D12_D13_2026-08-03"]
    assert "76,000+ units" in synth["respawn_condition_confirmed_live"]
    assert "worm (D12), Redbug (D09), and shell_bug (D13)" in synth["respawn_condition_confirmed_live"]
    assert "NEVER reproduce" in synth["respawn_condition_confirmed_live"]


def test_reinit_mechanism_cites_the_backlink_reinstantiation():
    doc = load_artifact()
    synth = doc["SYNTHESIZED_FROM_D09_D12_D13_2026-08-03"]
    mech = synth["reinit_mechanism_confirmed"]
    assert "0x80049C2C" in mech
    assert "backlink (+0x80)" in mech
    assert "0x80049CA4" in mech


def test_self_caught_correction_documented():
    doc = load_artifact()
    synth = doc["SYNTHESIZED_FROM_D09_D12_D13_2026-08-03"]
    corr = synth["self_caught_correction"]
    assert "a1=2" in corr
    assert "t0, not s0" in corr


def test_still_open_names_the_admission_check_contradiction_explicitly():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    contradiction = still_open["admission_check_unresolved_contradiction"]
    assert "0x8009EC50" in contradiction
    assert "OPPOSITE of the confirmed live behavior" in contradiction
    assert "NOT resolved" in contradiction


def test_donor_artifact_actually_backs_the_claims():
    donor = json.loads(DONOR.read_text())
    r = donor["RESPAWN_MECHANISM_2026-08-02"]
    assert "0x80049c2c" in r["asm_trace_the_actual_reinit_routine"].lower()
    assert "0x8009ec50" in r["asm_trace_the_admission_check_UNRESOLVED_CONTRADICTION"].lower()


def test_registry_status_is_partial_with_bounded_next():
    text = REGISTRY.read_text()
    start = text.index("  - id: D05_death_respawn")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "D05_death_respawn"
    assert row["status"] == "partial"
    assert "SYNTHESIZED FROM D09/D12/D13 2026-08-03" in " ".join(row["bindings"])
    assert "admission-check contradiction" in row["next"]

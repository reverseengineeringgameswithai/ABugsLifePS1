"""Guards for the D11 (mites and grubs) evidence -- mite half.

See ObsidianVault/Experiments/EXP_2026-08-02_phase4_d11_mite.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d11_mite.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_misattributed_old_fixtures_documented():
    doc = load_artifact()
    finding = doc["MISATTRIBUTED_OLD_FIXTURES_2026-08-02"]
    assert "id=12" in finding["grub_fixture_finding"]
    assert "D12 earthworm" in finding["grub_fixture_finding"]
    assert "WRONG and retracted" in finding["grub_fixture_finding"]
    assert "Birdnest" in finding["mite_fixture_finding"]
    assert "GRUB.ALL" in finding["asset_corroboration"]
    assert "NO 'MITE' asset" in finding["asset_corroboration"]


def test_identity_id37_is_mite():
    doc = load_artifact()
    identity = doc["IDENTITY_2026-08-02"]
    assert "id=37" in identity["result"]
    assert "canyon_bug" in identity["result"]
    assert "Mite was from the manual" in identity["operator_confirmation"]


def test_combat_timeline():
    doc = load_artifact()
    combat = doc["COMBAT_AND_DEATH_2026-08-02"]
    assert "f127" in combat["timeline"]
    assert "f155" in combat["timeline"]
    assert "f169" in combat["timeline"]
    assert "f203" in combat["timeline"]
    assert "f253" in combat["timeline"]
    assert "hp 2->1" in combat["timeline"]


def test_respawn_measured():
    doc = load_artifact()
    respawn = doc["RESPAWN_2026-08-02"]
    assert "frame 1073" in respawn["result"]
    assert "820 frames" in respawn["result"]
    assert "13.7 seconds" in respawn["result"]
    assert "not yet independently measured" in respawn["cross_validation_status"]


def test_grub_half_resolved():
    doc = load_artifact()
    grub = doc["GRUB_HALF_RESOLVED_2026-08-02"]
    assert "id=12" in grub["trigger"]
    assert "we already established this" in grub["visual_confirmation"]
    assert "never-visually-verified" in grub["identity_correction"]
    assert "NO ARMOR AT ALL" in grub["characterization_already_exists_under_d12"]


def test_still_open_no_longer_names_grub_half_as_missing():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "grub half of this row" not in still_open
    assert "earthworm" in still_open.lower()


def test_mite_type_word_closed():
    doc = load_artifact()
    tw = doc["MITE_TYPE_WORD_2026-08-02"]
    assert "0x0125" in tw["result"]
    assert "37" in tw["result"]
    assert "closes" in tw["closes"].lower()


def test_mite_aggro_confirmed_negative():
    doc = load_artifact()
    aggro = doc["AGGRO_2026-08-02"]
    assert "0x4011 -> 0x4013" in aggro["result"]
    assert "AWAY" in aggro["result"]
    assert "shell_bug" in aggro["result"]
    assert "does NOT chase" in aggro["result"]


def test_still_open_no_longer_names_mite_aggro_or_typeword():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "which specific chunk-31 kind/type-word maps to id=37" not in still_open
    assert "mite-specific aggro/chase behavior" not in still_open


def test_exhaustion_assessment_documented():
    doc = load_artifact()
    exhaustion = doc["EXHAUSTION_ASSESSMENT_2026-08-02"]
    assert exhaustion["assessment"].startswith("BOUNDED PARTIAL")
    assert "Move to a different unresolved row" in exhaustion["decision"]
    assert "does not upgrade either row's status" in exhaustion["decision"]


def test_registry_status_is_partial_not_solved():
    text = REGISTRY.read_text()
    start = text.index("  - id: D11_mites_grubs")
    end = text.index("  - id: D12_centipedes_earthworms")
    block = text[start:end]
    assert "status: partial" in block
    assert "status: solved" not in block
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "D11_mites_grubs"
    assert row["status"] == "partial"

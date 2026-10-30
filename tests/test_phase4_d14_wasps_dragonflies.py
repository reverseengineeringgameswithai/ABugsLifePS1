"""Guards for the D14 (wasps/dragonflies family) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_d14_wasps_dragonflies.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d14_wasps_dragonflies.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_artifact_status_is_bounded_exhausted():
    doc = load_artifact()
    assert doc["status"] == "bounded_exhausted"
    assert doc["disposition"] == "move_on"


def test_family_bindings_identify_both_species():
    doc = load_artifact()
    fb = doc["family_bindings"]
    assert fb["dragonfly"]["actor_id"] == 34
    assert fb["dragonfly"]["callback"] == "0x8004A20C"
    assert fb["wasp_internal_bee"]["actor_id"] == 13
    assert fb["wasp_internal_bee"]["callback"] == "0x8004A144"


def test_dragonfly_has_no_strike_section():
    doc = load_artifact()
    assert "no species strike section" in doc["static_findings"]["dragonfly_navigation"]


def test_bee_contact_causally_confirmed():
    doc = load_artifact()
    bee = doc["runtime_findings"]["bee_contact"]
    assert bee["contact_transition_frame"] == 25958
    assert bee["native_strike_frame"] == 25994
    assert bee["health_before_after"] == [4, 3]


def test_targetability_positive_and_negative_controls_present():
    doc = load_artifact()
    t = doc["runtime_findings"]["targetability"]
    assert "0x4007" in t["bee_positive"]
    assert "0x1006" in t["bee_negative_switch"]


def test_negative_controls_documented():
    doc = load_artifact()
    nc = doc["negative_controls"]
    assert "zero" in nc["bee_no_input"].lower()
    assert "600 frames" in nc["bee_no_input"]


def test_closure_rationale_scopes_shared_system_out():
    doc = load_artifact()
    rationale = doc["closure_rationale"]
    assert "shared-system work" in rationale


def test_evidence_hashes_present_for_reproducibility():
    doc = load_artifact()
    hashes = doc["evidence_hashes"]
    assert len(hashes) >= 10
    assert all(isinstance(v, str) and len(v) >= 40 for v in hashes.values())


def test_registry_status_is_partial_not_unresolved():
    text = REGISTRY.read_text()
    start = text.index("  - id: D14_wasps_dragonflies")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "status: partial" in block
    assert "status: unresolved" not in block
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "D14_wasps_dragonflies"
    assert row["status"] == "partial"
    assert "0x8004A20C" in " ".join(row["bindings"])
    assert "0x8004A144" in " ".join(row["bindings"])


def test_registry_bindings_cite_the_bounded_exhaustion_pass():
    text = REGISTRY.read_text()
    start = text.index("  - id: D14_wasps_dragonflies")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "BOUNDED EXHAUSTION 2026-08-03" in block
    assert "25958" in block
    assert "25994" in block


def test_registry_missing_field_reflects_banking_gap_not_open_facts():
    text = REGISTRY.read_text()
    start = text.index("  - id: D14_wasps_dragonflies")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "banking gap" in block.lower()

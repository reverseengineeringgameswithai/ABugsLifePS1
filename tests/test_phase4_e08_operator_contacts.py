"""Guards for natural E08 actor outcomes from existing operator movies."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_e08_operator_contacts as contacts  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_e08_operator_contacts.json"
ARTIFACT_SHA256 = "135abb3c74f68c372482eb8b69e54563d0c83eda8d4869c5ee19b0ce3d9a24e5"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


@pytest.mark.local_media
def test_operator_contact_fixture_census_recomputes_from_central_pins():
    retained = load_artifact()["fixture_census"]
    assert contacts.build_fixture_census() == retained
    assert retained["count"] == 5
    assert all(row["movie"]["version"] == 3 for row in retained["pairs"])
    assert all(row["save"]["media_class"] == "pristine"
               for row in retained["pairs"])


def test_retained_operator_contact_outcomes_recompute_without_summary_flags():
    document = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert contacts.evidence_gaps(document) == []
    assert document["summary"] == {
        "movies_replayed": 5,
        "controlled_type_words": ["0x060c", "0x0b11", "0x0c13", "0x0f06"],
        "newly_controlled_unclassified_type_words": ["0x060c"],
        "unclassified_with_native_outcome_controls": 19,
        "unclassified_without_native_outcome_control": 28,
        "remaining_uncontrolled_type_words": [
            "0x040f", "0x050d", "0x0603", "0x0605", "0x061a",
            "0x0a0a", "0x0b1d", "0x0c01", "0x0c02", "0x0c04",
            "0x0c08", "0x0e14", "0x1119", "0x1321", "0x1407",
            "0x1712", "0x1807", "0x1b1f", "0x1c16", "0x1d1e",
            "0x1e20", "0x1f04", "0x201b", "0x2117", "0x2118",
            "0x2223", "0x2528", "0x2629"],
        "species_or_row_owners_promoted": 0,
    }
    assert [row["typed_outcome_observed"] for row in document["replays"]] == \
        [True, True, True, False, True]
    assert all(
        replay["cycle_neutral_trace"]["comparison"]["cycle_neutral"] is True
        for replay in document["replays"])


def test_low_level_outcome_and_trace_mutations_turn_the_e08_extension_red():
    document = load_artifact()
    mutated = copy.deepcopy(document)
    boundary = mutated["replays"][2]["native_outcome_boundaries"][0]
    boundary["after"]["actor"] = copy.deepcopy(boundary["before"]["actor"])
    assert "native outcome boundary" in " ".join(contacts.evidence_gaps(mutated))

    mutated = copy.deepcopy(document)
    mutated["replays"][0]["cycle_neutral_trace"]["comparison"][
        "cycle_neutral"] = False
    assert "cycle-neutral trace" in " ".join(contacts.evidence_gaps(mutated))

    mutated = copy.deepcopy(document)
    mutated["summary"]["newly_controlled_unclassified_type_words"] = []
    assert "partition" in " ".join(contacts.evidence_gaps(mutated))


def test_operator_leads_do_not_complete_e08_or_promote_species_owners():
    document = load_artifact()
    assert document["bounded_interpretation"]["forbidden_claim"].startswith(
        "Do not assign a D-row species")
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "props_movers_gates")
    assert campaign["status"] == "active"
    assert common.audit_campaign(campaign, registry, common.finding_index()) == [
        "props_movers_gates: status is not completed"]
    coverage = phase4_coverage.build()
    assert coverage["rows"]["E08_props_movers_gates"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91


def test_props_schema_routes_only_the_aggregate_native_outcome_frontier():
    schema = yaml.safe_load((ROOT / "config/phase4_props_movers.yaml").read_text())
    frontier = schema["native_contact_outcome_frontier"]
    assert schema["schema"] == "abl-phase4-props-movers/5"
    assert frontier["aggregate_unclassified_with_native_outcome_controls"] == 19
    assert frontier["aggregate_unclassified_without_native_outcome_control"] == 28
    assert frontier["new_natural_outcome_type_words"] == ["0x060C"]
    assert frontier["species_or_row_owners_promoted"] == 0

"""WP3 independent fixed-width domain and consumer census guards."""
import json
from copy import deepcopy
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import phase3_native_domains as domains  # noqa: E402


def _load():
    retained = json.loads((ROOT / "analysis/phase3_native_domains.json").read_text())
    computed = domains.build()
    a, b = dict(retained), dict(computed)
    a.pop("generated", None)
    b.pop("generated", None)
    assert a == b
    return computed


def test_census_is_fresh_and_independently_exhaustive():
    doc = _load()
    assert doc["exhaustive"] is True
    assert doc["independent_universe_errors"] == []
    assert doc["unknown_campaign_scope_ids"] == []
    assert doc["unscoped_semantic_scalar_ids"] == []
    assert set(doc["exhaustive_over"]) == {
        "campaign_state_manifest", "typed_record_fields",
        "decoded_dispatch_selectors",
    }


def test_removing_a_semantic_entry_is_detected_by_the_independent_scope():
    sem = yaml.safe_load((ROOT / "config/semantic_state.yaml").read_text())
    scope = yaml.safe_load(
        (ROOT / "config/phase3_campaign_state_scope.yaml").read_text())
    damaged = deepcopy(sem)
    victim = "original.player_equipped_berry"
    damaged["entries"] = [row for row in damaged["entries"] if row["id"] != victim]
    unknown, _unscoped = domains.scope_semantic_gaps(damaged, scope)
    assert victim in unknown


def test_adding_a_scalar_without_campaign_scope_is_detected():
    sem = yaml.safe_load((ROOT / "config/semantic_state.yaml").read_text())
    scope = yaml.safe_load(
        (ROOT / "config/phase3_campaign_state_scope.yaml").read_text())
    damaged = deepcopy(sem)
    damaged["entries"].append({
        "id": "original.silent_selector", "namespace": "original",
        "address": 0x80082000, "width": "u8",
    })
    _unknown, unscoped = domains.scope_semantic_gaps(damaged, scope)
    assert "original.silent_selector" in unscoped


def test_every_typed_record_field_and_decoded_dispatch_has_a_domain_row():
    doc = _load()
    records = yaml.safe_load((ROOT / "config/record_types.yaml").read_text())
    field_count = sum(len(row["fields"]) for row in records["records"])
    jr = json.loads((ROOT / "analysis/phase3_jr_tables.json").read_text())
    assert doc["counts"]["typed_record_field_domains"] == field_count
    assert doc["counts"]["decoded_dispatch_selector_domains"] == \
        jr["classification"]["table_dispatch"]


def test_every_domain_has_consumers_and_unknowns_have_structured_blockers():
    doc = _load()
    for row in doc["domains"]:
        assert row["id"] and row["width"] and row["domain"]
        assert row["consumers"] and row["evidence"]
        if row["status"] != "resolved":
            assert set(row["blocker"]) >= {
                "missing_link", "evidence", "next_experiment",
            }

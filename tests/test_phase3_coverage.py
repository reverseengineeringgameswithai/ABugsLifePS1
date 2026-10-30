"""Binding WP1-WP9 coverage guard.

The historical gate passed by checking representative artifacts.  These tests
pin the stricter contract surface: omitted record families, lifecycle models,
exceptional routes, call reports, and contradiction evidence remain visible and
keep the phase open.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase3_coverage_matrix as coverage  # noqa: E402


def _without_date(doc):
    clean = dict(doc)
    clean.pop("generated", None)
    return clean


def test_retained_matrix_is_a_fresh_low_level_recomputation():
    retained = json.loads((ROOT / "analysis/phase3_coverage_matrix.json").read_text())
    assert _without_date(retained) == _without_date(coverage.build_matrix())


def test_all_nine_binding_packages_are_present_and_directly_met():
    matrix = coverage.build_matrix()
    assert set(matrix["work_packages"]) == {f"WP{i}" for i in range(1, 10)}
    assert matrix["overall_met"] is True
    assert [key for key, row in matrix["work_packages"].items() if not row["met"]] == []


def test_wp1_requires_a_semantic_frontier_not_only_addresses():
    wp = coverage.build_matrix()["work_packages"]["WP1"]
    assert wp["required_facets"] == [
        "functions", "state", "assets", "overlay", "readers", "writers", "lifecycle"
    ]
    assert wp["rows_with_open_frontier"] == {}
    assert wp["mechanics"] == 107 and wp["address_bound"] == 106
    # The closure remains falsifiable: an empty facet is not evidence, while a
    # complete three-part blocker is an explicit bounded frontier.
    assert coverage._frontier_facet_bounded({"assets": []}, "assets") is False
    assert coverage._frontier_facet_bounded({
        "assets": [],
        "frontier_blockers": {"assets": {
            "missing_link": "unknown asset",
            "evidence": "artifact:row",
            "next_experiment": "trace the loader",
        }},
    }, "assets") is True


def test_wp2_and_wp3_require_explicit_exhaustive_scope_manifests():
    packages = coverage.build_matrix()["work_packages"]
    assert packages["WP2"]["met"] is True
    assert packages["WP2"]["missing_scope_groups"] == []
    assert packages["WP2"]["scope_manifest_gaps"] == []
    assert packages["WP2"]["addressed_entries"] == packages["WP2"]["lifetime_entries"] == 63
    assert packages["WP3"]["met"] is True
    assert packages["WP3"]["domain_rows"] == 134
    assert packages["WP3"]["independent_universe"] == {
        "campaign_state_domains": 36,
        "typed_record_field_domains": 62,
        "decoded_dispatch_selector_domains": 36,
        "total": 134,
    }
    assert packages["WP3"]["domain_gaps"] == []


def test_wp5_does_not_collapse_required_record_families_into_actor_or_state_findings():
    wp = coverage.build_matrix()["work_packages"]["WP5"]
    assert set(wp["required_record_families"]) == {
        "object", "contact", "enemy", "projectile", "seed", "plant", "player",
        "camera", "render", "audio", "objective", "frontend",
    }
    assert wp["missing_record_families"] == []
    assert wp["represented_by"]["object"] == ["actor_record"]
    assert wp["represented_by"]["enemy"] == ["actor_record"]
    assert wp["represented_by"]["audio"] == ["sfx_voice_slot"]
    assert wp["represented_by"]["frontend"] == ["frontend_progress_record"]
    assert (wp["known_bytes"], wp["total_bytes"]) == (181, 524)
    assert wp["met"] is True


def test_wp6_requires_every_ownership_lifecycle_dimension_per_family():
    wp = coverage.build_matrix()["work_packages"]["WP6"]
    assert wp["required_model_fields"] == [
        "capacity", "slot_reuse", "ownership_transfer", "retirement", "reset"
    ]
    assert wp["ownership_model_gaps"] == {}
    assert wp["contact_peak_alloc_occupied"] == 4
    assert wp["met"] is True


def test_wp7_and_wp8_require_mapped_surfaces_and_exhaustive_reports():
    packages = coverage.build_matrix()["work_packages"]
    wp7 = packages["WP7"]
    assert wp7["gaps"] == []
    assert wp7["exceptional_routes_complete"] is True
    assert wp7["unload_graph_complete"] is True
    assert wp7["met"] is True
    wp8 = packages["WP8"]
    assert wp8["reader_writer_report_complete"] is True
    assert wp8["caller_callee_report_complete"] is True
    assert wp8["asset_provenance_report_complete"] is True
    assert wp8["met"] is True


def test_wp9_surfaces_are_reconciled_without_promoting_bounded_unknowns():
    wp = coverage.build_matrix()["work_packages"]["WP9"]
    assert wp["machine_statuses_reconciled"] is True
    assert wp["contradiction_gaps"] == []
    assert wp["documentation_contradictions"] == []
    assert (wp["a07_status"], wp["f09_status"], wp["d18_status"]) == (
        "external_lead", "partial", "partial"
    )
    assert wp["met"] is True

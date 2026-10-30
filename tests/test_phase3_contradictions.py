"""WP9 contradiction reconciliation is derived and falsifiable."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase3_contradictions as contradictions  # noqa: E402


def without_date(doc):
    clean = dict(doc)
    clean.pop("generated", None)
    return clean


def test_retained_ledger_is_fresh_and_checks_every_required_source_class():
    retained = json.loads((ROOT / "analysis/phase3_contradictions.json").read_text())
    assert without_date(retained) == without_date(contradictions.build_ledger())
    categories = {row["category"] for row in retained["sources_checked"]}
    assert {"disassembly", "C", "runtime_evidence", "asset_observations",
            "schemas", "registries", "generated_artifacts", "debugger_toolchain",
            "Canon", "roadmap"} <= categories


def test_every_contradiction_is_reconciled_or_explicitly_bounded():
    doc = contradictions.build_ledger()
    assert doc["summary"]["open"] == []
    assert all(row["predicate_met"] for row in doc["contradictions"])
    assert all(row["status"] in {"reconciled", "bounded"}
               for row in doc["contradictions"])
    assert all(row["residual"] for row in doc["contradictions"]
               if row["status"] == "bounded")


def test_a07_cannot_regress_to_absolute_disproof():
    row = {r["id"]: r for r in contradictions.build_ledger()["contradictions"]}[
        "a07_absolute_disproof_vs_bounded_negative"]
    assert row["status"] == "bounded"
    assert "external lead" in row["resolution"]
    assert "exact input sequence" in row["residual"]


def test_render_snapshots_cannot_regress_to_invented_loader_causality():
    row = {r["id"]: r for r in contradictions.build_ledger()["contradictions"]}[
        "render_snapshot_variance_vs_loader_causality"]
    assert row["status"] == "bounded"
    assert "do not observe the writes" in row["observation"]
    assert "writer PCs" in row["residual"]


def test_actor_y_absence_cannot_outrun_retained_candidates():
    row = {r["id"]: r for r in contradictions.build_ledger()["contradictions"]}[
        "actor_y_absence_claim_vs_retained_evidence"]
    assert row["status"] == "bounded"
    assert "one Level01 actor" in row["observation"]
    assert "every aligned field candidate" in row["residual"]


def test_duckstation_api_docs_cannot_regress_to_the_obsolete_method_surface():
    row = {r["id"]: r for r in contradictions.build_ledger()["contradictions"]}[
        "duckstation_api_prose_vs_exact_phase3_fork"]
    assert row["status"] == "reconciled"
    assert "203 dispatched methods" in row["observation"]
    assert "current-fork drift" in row["resolution"]


def test_recovered_hook_confidence_cannot_be_hidden_by_post_build_discharge():
    row = {r["id"]: r for r in contradictions.build_ledger()["contradictions"]}[
        "hook_discharge_vs_degraded_recovered_extent"]
    assert row["status"] == "bounded"
    assert "both" in row["observation"] and "degraded" in row["observation"]
    assert "9 exact discharges + 1 degraded" in row["resolution"]


def test_training_pin_cannot_masquerade_as_reproduced_cold_boot_evidence():
    row = {r["id"]: r for r in contradictions.build_ledger()["contradictions"]}[
        "training_fixture_pin_vs_actual_cold_boot_regeneration"]
    assert row["status"] == "reconciled"
    assert "index 0 to 6904" in row["resolution"]
    assert "exact config-owned PID" in row["resolution"]

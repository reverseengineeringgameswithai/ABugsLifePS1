"""Guards for offline-only C15 capsule-consumer reconciliation."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_reconcile_capsule_consumers as reconcile  # noqa: E402


def test_reconciliation_is_current_and_preserves_live_payload():
    report = json.loads(reconcile.OUTPUT.read_text())
    artifact = json.loads(reconcile.ARTIFACT.read_text())
    assert report["schema"] == "abl-phase4-capsule-consumer-reconciliation/1"
    assert report["valid"] is True and report["errors"] == []
    assert report["allowed_top_level_changes"] == [
        "capsule_first_lane", "source_dependencies"]
    assert report["historical_live_provenance_preserved"] is True
    assert report["live_replay_required"] is False
    assert report["relevant_capsule_queries_identical"] is True
    assert report["current_capsule_count"] == 55
    assert report["current_movie_count"] == 55
    assert artifact["run_provenance"]["generator_sha256"] == \
        report["historical_live_generator_sha256"]
    assert hashlib.sha256(reconcile.ARTIFACT.read_bytes()).hexdigest() == \
        report["artifact_sha256_after"]


def test_reconciliation_rebuilds_identically_from_exact_reader_queries():
    artifact, report = reconcile.build(verify_external=False)
    assert reconcile.artifact_rendered(artifact) == reconcile.ARTIFACT.read_bytes()
    assert reconcile.report_rendered(report) == reconcile.OUTPUT.read_bytes()

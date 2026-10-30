"""Guards for metadata-only C16 dependency reconciliation."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common  # noqa: E402
import phase4_reconcile_baseline_dependencies as reconcile  # noqa: E402


def test_reconciliation_is_current_bounded_and_payload_preserving():
    report = json.loads(reconcile.OUTPUT.read_text())
    assert report["schema"] == "abl-phase4-baseline-dependency-reconciliation/1"
    assert report["valid"] is True and report["errors"] == []
    assert report["allowed_changed_rows"] == ["A10_handstand", "A11_seed_as_weapon"]
    assert len(report["artifacts"]) == 3
    assert all(row["only_source_dependency_metadata_changed"] for row in report["artifacts"])
    assert all(row["current_context_matches_retained_artifact"] for row in report["artifacts"])
    assert all(row["baseline_sha256_after"] == phase4_common.sha256(reconcile.BASELINE)
               for row in report["artifacts"])


def test_reconciliation_rebuilds_identically():
    updates, report = reconcile.build()
    assert reconcile.rendered(report) == reconcile.OUTPUT.read_bytes()
    assert all(path.read_bytes() == reconcile.artifact_rendered(document)
               for path, document in updates)

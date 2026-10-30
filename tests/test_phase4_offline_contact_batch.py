"""Falsifiable guards for the first Phase-4 offline contact/hazard batch."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common  # noqa: E402


SUMMARY = ROOT / "analysis/phase4_offline_contact_batch.json"
CAPSULES = ROOT / "analysis/phase4_trace_capsule_set.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_batch_is_current_top_five_and_scans_every_relevant_capsule():
    document = load(SUMMARY)
    assert document["schema"] == "abl-phase4-offline-contact-batch/1"
    assert document["valid"] is True
    assert document["errors"] == []
    assert document["queue_counts"] == {
        "complete": 16,
        "live_required": 6,
        "no_capsule": 68,
        "offline_partial": 7,
        "offline_ready": 26,
        "open": 91,
        "rows": 107,
    }
    assert [row["row_id"] for row in document["selected_rows"]] == [
        "E10_hazards", "D11_mites_grubs", "D08_flies",
        "D09_cockroaches", "D15_daddy_long_legs",
    ]
    assert [row["queue_rank"] for row in document["selected_rows"]] == [1, 2, 3, 4, 5]
    assert all(row["classification"] == "offline_ready" for row in document["selected_rows"])
    assert document["offline_batch"]["capsule_count"] == 13
    assert document["offline_batch"]["reconstructed_records"] == 5753
    assert len(document["capsule_summaries"]) == 13
    assert sum(row["records"] for row in document["capsule_summaries"]) == 5753


def test_batch_pins_reader_capsules_sources_and_external_index():
    document = load(SUMMARY)
    capsule_index = load(CAPSULES)
    reader = capsule_index["offline_reader_snapshot"]
    assert document["offline_batch"]["reader_path"] == reader["absolute_path"]
    assert document["offline_batch"]["reader_sha256"] == reader["sha256"]
    assert phase4_common.sha256(Path(reader["absolute_path"])) == reader["sha256"]
    current = {row["movie"]: row for row in capsule_index["capsules"]}
    for summary in document["capsule_summaries"]:
        capsule = current[summary["movie"]]
        assert summary["movie_sha256"] == capsule["movie_sha256"]
        assert summary["capsule_manifest_sha256"] == capsule["capsule_manifest_sha256"]
        assert summary["capsule_tree_sha256"] == capsule["capsule_tree_sha256"]
    for relative, expected in document["source_dependencies"].items():
        assert phase4_common.sha256(ROOT / relative) == expected
    external = document["external_index"]
    external_path = Path(external["absolute_path"])
    assert external["media_class"] == "external game-derived evidence; never commit"
    assert external["preservation_required"] is True
    assert external_path.stat().st_size == external["bytes"]
    assert phase4_common.sha256(external_path) == external["sha256"]


def test_batch_retains_bounded_outcomes_without_species_or_writer_overclaim():
    document = load(SUMMARY)
    findings = document["derived_findings"]
    assert findings["movie_count"] == 13
    assert findings["health_change_events"] == 11
    assert findings["life_change_events"] == 4
    assert findings["actor_hp_change_events"] == 12
    assert set(findings["health_event_domain_correlations"].values()) == {11}
    assert len(findings["actor_ids_observed"]) == 29
    assert document["live_escalation"] is None
    joined = " ".join(document["bounded_conclusions"])
    assert "filenames do not establish species or hazard ownership" in joined
    assert "does not attribute an exact writer" in joined
    assert set(document["named_unknowns"]) == {
        "E10_hazards", "D08_flies", "D09_cockroaches",
        "D11_mites_grubs", "D15_daddy_long_legs",
    }

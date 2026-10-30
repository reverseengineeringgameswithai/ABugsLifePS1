"""CI-safe guards for the hash-only Phase-4 trace-capsule preservation index."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "analysis" / "phase4_trace_capsule_set.json"


def load_report():
    return json.loads(REPORT.read_text())


def test_trace_capsule_set_is_complete_and_control_matched():
    doc = load_report()
    assert doc["schema"] == "abl-phase4-trace-capsule-set-v1"
    assert doc["authority"].startswith("hash-verified pristine SCUS-94288")
    assert doc["complete"] is True
    assert doc["errors"] == []
    assert doc["movie_count"] == doc["capsule_count"] == 50
    assert doc["total_movie_frames"] > 0
    assert doc["total_external_bytes"] > 0
    assert len(doc["capsules"]) == doc["capsule_count"]
    for row in doc["capsules"]:
        assert row["control_match"] is True
        assert row["preservation_required"] is True
        assert row["media_class"].endswith("never commit")
        for key in ("movie_sha256", "capsule_manifest_sha256", "capsule_tree_sha256",
                    "duckstation_binary_sha256"):
            assert len(row[key]) == 64, (row["movie"], key)
        assert row["movie"].startswith("movies/Phase4/") and row["movie_bytes"] > 0
        assert row["start_state"]["path"].startswith("movies/Phase4/")
        assert set(row["start_state"]) == {"path", "sha256", "bytes"}


def test_trace_capsule_external_dependencies_and_reproduction_are_pinned():
    doc = load_report()
    binary = doc["duckstation_binary_snapshot"]
    source = doc["duckstation_source_snapshot"]
    reader = doc["offline_reader_snapshot"]
    assert len(binary["sha256"]) == len(source["sha256"]) == len(reader["sha256"]) == 64
    assert binary["bytes"] > 0 and source["bytes"] > 0 and reader["bytes"] > 0
    assert doc["preservation_contract"]["offline_reader"] == reader
    assert {row["duckstation_binary_sha256"] for row in doc["capsules"]} == {binary["sha256"]}
    assert len(doc["pristine_media"]) == 2
    assert all(len(row["sha256"]) == 64 for row in doc["pristine_media"])

    comparison = doc["reproducibility_comparison"]
    assert comparison["requested"] == doc["capsule_count"]
    assert comparison["exact_capsules"] == doc["capsule_count"]
    assert comparison["frame_chunks_byte_identical"] is True
    assert comparison["mismatches"] == []
    assert "session/host serialization" in comparison["checkpoint_note"]

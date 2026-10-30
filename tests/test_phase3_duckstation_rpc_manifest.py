"""Freshness guards for the DuckStation source-pinned RPC census."""
import json
from pathlib import Path

import pytest

import phase3_duckstation_rpc_manifest as rpc_manifest


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
MARKDOWN_PATH = ROOT / "tools/duckstation_rpc_method_manifest.md"
CANON_PATH = ROOT / "ObsidianVault/Canon/Indexes/DuckStation_API_Index.md"


def retained():
    return json.loads(JSON_PATH.read_text())


def test_retained_method_sets_counts_markdown_and_canon_recompute_cleanly():
    doc = retained()
    gaps = rpc_manifest.retained_gaps(
        doc, MARKDOWN_PATH.read_text(), CANON_PATH.read_text())
    assert gaps == []
    assert doc["methods"]["counts"] == {
        "committed": 114,
        "dirty_only": 106,
        "removed_from_head": 0,
        "current": 220,
    }
    assert doc["source"]["revision"] == \
        "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5"
    assert doc["source"]["status_line_count"] == 106


def test_guard_rejects_a_stale_count_list_and_canon_surface():
    doc = retained()
    omitted = doc["methods"]["dirty_only"][-1]
    doc["methods"]["current"].remove(omitted)
    doc["methods"]["counts"]["current"] -= 1
    stale_markdown = rpc_manifest.render_markdown(doc)
    stale_canon = CANON_PATH.read_text().replace(
        doc["source"]["dispatcher_sha256"], "0" * 64)
    gaps = rpc_manifest.retained_gaps(doc, stale_markdown, stale_canon)
    assert any("dirty-only methods" in gap for gap in gaps)
    assert any("Canon API index omits" in gap for gap in gaps)


def test_current_fork_comparison_is_a_distinct_low_level_predicate():
    doc = retained()
    doc["binaries"]["build-release/bin/duckstation-qt"]["sha256"] = "0" * 64
    gaps = rpc_manifest.current_fork_gaps(doc, Path.home() / "duckstation")
    assert gaps == [
        "retained JSON differs from fresh DuckStation source/binary extraction"]


@pytest.mark.local_media
def test_retained_manifest_matches_the_exact_current_duckstation_worktree():
    doc = retained()
    fresh = rpc_manifest.build_manifest(Path.home() / "duckstation")
    assert rpc_manifest.semantic(doc) == rpc_manifest.semantic(fresh)

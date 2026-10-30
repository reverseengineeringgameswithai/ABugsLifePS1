"""WP8 exhaustive call-graph and asset-provenance report guards."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_call_report_covers_every_code_boundary_and_keeps_indirect_edges_explicit():
    report = json.loads((ROOT / "analysis/phase3_call_graph.json").read_text())
    source = json.loads((ROOT / "analysis/functions.json").read_text())
    expected = sum(row.get("range_type") in ("code", "thunk")
                   for row in source["functions"])
    assert report["exhaustive"] is True
    assert len(report["functions"]) == expected == report["summary"]["functions"]
    assert set(report["callers"]) == set(report["callees"]) == set(report["functions"])
    assert set(report["indirect_edges"]) >= {"jr", "jalr", "reason"}


def test_asset_report_covers_every_pin_and_every_required_family():
    report = json.loads((ROOT / "analysis/phase3_asset_provenance.json").read_text())
    baseline = json.loads((ROOT / "tools/build_baselines.json").read_text())
    assert report["exhaustive"] is True
    assert set(report["assets"]) == set(baseline["staged_inputs"])
    assert all(row["local_hash_matches_pin"] for row in report["assets"].values())
    assert report["summary"]["missing_required_roles"] == []
    assert set(report["summary"]["role_counts"]) >= {
        "geometry", "collision", "textures", "models", "animation",
        "audio", "fmv", "ui", "level_specific",
    }
    assert all(row["load_owners"] for row in report["assets"].values())

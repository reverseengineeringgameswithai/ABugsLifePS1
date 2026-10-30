from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_finale_route_probe as probe  # noqa: E402


def _raw() -> dict:
    return json.loads(
        (probe.EXTERNAL_ROOT /
         probe._spec("result")["relative_path"]).read_text())


def test_summary_rebuilds_from_hash_pinned_negative_route_checks():
    document = probe.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["record_counts"] == {
        "cycle_neutral_queries": 4,
        "coverage_ranges": 4,
        "complete_consumption_queries": 2,
        "bare_pc_alias_hits": 326,
        "resident_finale_route_hits": 0,
        "debugger_cleanup_actions": 10,
    }
    assert document["observation"]["resident_finale_c_hits"] == 0
    assert document["observation"]["resident_finale_d_hits"] == 0
    assert document["observation"]["complete_consumption"] is True
    assert document["observation"]["consumed_frame_count"] == 33268
    assert document["observation"]["final_consumed_input_index"] == 33267
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert probe.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n")


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (lambda row: row["full_finale_c_selector_filtered"]["trace"][
            "comparison"].update({"same_ram": False}),
         "cycle-neutral comparison"),
        (lambda row: row["full_finale_c_selector_filtered"].update(
            {"register_filter": None}),
         "target/consumption/filter"),
        (lambda row: row["full_finale_c_selector_filtered"].update(
            {"target_frame": 33267, "complete_consumption": False}),
         "target/consumption/filter"),
        (lambda row: row["full_finale_c_selector_filtered"][
            "movie_status"].update({
                "playing": True, "playback_index": 33267,
                "reproducible": True,
            }),
         "complete movie consumption"),
        (lambda row: row["full_finale_c_selector_filtered"]["trace"][
            "coverage"][0]["coverage"].update({
                "total_hits": 1,
                "distinct_pc_count": 1,
                "pcs": ["0x80050284"],
            }),
         "coverage result"),
        (lambda row: row["full_finale_d_bare_pc"]["trace"][
            "instrumented"].update({"cycle": 18836452126}),
         "endpoint signature"),
        (lambda row: row["cleanup"][0].update({"ok": False}),
         "instrumentation cleanup"),
    ],
)
def test_low_level_mutations_are_rejected(mutator, error):
    document = copy.deepcopy(_raw())
    mutator(document)
    if error == "instrumentation cleanup":
        with pytest.raises(ValueError, match=error):
            probe._validate_cleanup(document)
    else:
        with pytest.raises(ValueError, match=error):
            probe.validate_result(document, verify_identity=False)

"""Offline validation of the Phase-1 live-census artifact.

Guards analysis/phase1_kind_actor_census.json: internal consistency (counts,
histograms, rollups), clean partitions (Canon-bound vs explicit-unknown), the
cross-level kind-extent proof, full stage coverage, absence of per-level errors,
and (local_media) the recorded save-state hashes against the files on disk.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "analysis" / "phase1_kind_actor_census.json").read_text())

EXPECTED_LEVELS = ["training"] + [
    "stage01_anthill", "stage02_tunnels", "stage03_council_chamber",
    "stage04_cliffside_canyon", "stage05_riverbed_run", "stage06_birdnest",
    "stage07_city_entrance", "stage08_city_square", "stage09_bug_bar",
    "stage10_clover_forest", "stage11_the_tree", "stage12_battle_arena",
    "stage13_anthill_two", "stage14_riverbed_flight", "stage15_canyon_showdown",
]


def test_stage_coverage_and_no_errors():
    levels = DOC["levels"]
    assert sorted(levels) == sorted(EXPECTED_LEVELS)
    for lbl, lv in levels.items():
        assert "error" not in lv, f"{lbl}: {lv.get('error')}"
        for field in ("save", "save_sha256", "player_xyz", "actor_records",
                      "actor_id_histogram", "kind_table"):
            assert field in lv, f"{lbl} missing {field}"


def test_media_identity():
    assert DOC["media"]["serial"] == "SCUS-94288"


def test_actor_histograms_match_records():
    for lbl, lv in DOC["levels"].items():
        hist = {int(k): v for k, v in lv["actor_id_histogram"].items()}
        counted: dict = {}
        for rec in lv["actor_records"]:
            counted[rec["id"]] = counted.get(rec["id"], 0) + 1
        assert hist == counted, lbl


def test_actor_rollup_and_partition():
    observed = sorted({rec["id"] for lv in DOC["levels"].values()
                       for rec in lv["actor_records"]})
    assert observed == DOC["actor_ids_observed"]
    bound = {int(k) for k in DOC["actor_ids_with_canon_binding"]}
    unknown = set(DOC["actor_ids_unknown_role"])
    assert bound.isdisjoint(unknown)
    assert bound | unknown == set(observed)
    # the two Canon bindings that anchored the census method
    assert 16 in bound and 14 in bound  # Thumper, Dot


def test_kind_extent_proof():
    proof = DOC["kind_extent_proof"]
    breaks = proof["first_break_per_level"]
    assert sorted(breaks) == sorted(EXPECTED_LEVELS)
    assert proof["derived_extent"] == min(breaks.values()) == 50
    assert proof["levels_breaking_exactly_at_extent"], \
        "no level breaks at the derived extent — intersection rule unsupported"
    # past-end slots must NOT behave like a real table: their plausibility varies
    rejected = proof["rejected_past_end_slots_by_level"]
    per_level_sets = {lbl: {r["slot"] for r in rej} for lbl, rej in rejected.items()}
    assert len({frozenset(s) for s in per_level_sets.values()}) > 1, \
        "past-end plausible slots identical across levels — extent may be wrong"


def test_kind_tables_trimmed_to_extent_with_descriptors():
    extent = DOC["kind_extent_proof"]["derived_extent"]
    assert DOC["kinds_with_descriptors"] == list(range(extent))
    for lbl, lv in DOC["levels"].items():
        kt = lv["kind_table"]
        assert sorted(int(k) for k in kt) == list(range(extent)), lbl
        for k, v in kt.items():
            assert v["descriptor_hex"] and len(v["descriptor_hex"]) == 24, f"{lbl}/{k}"
            assert int(v["ptr"], 16) >= 0x80000000, f"{lbl}/{k}"


def test_kind_partition():
    kinds = set(DOC["kinds_with_descriptors"])
    bound = {int(k) for k in DOC["kinds_with_canon_binding"]}
    unknown = set(DOC["kinds_unknown_role"])
    assert bound.isdisjoint(unknown)
    assert bound | unknown == kinds


def test_addendum_probes_regenerate_with_artifact():
    add = DOC["addendum_probes"]
    thud = add["thud_boss_movie.movie.sav"]
    assert thud["records"] == 0, "Thud anchor now shows chunk-31 records — update row F09"
    for anchor in ("hopper_boss.movie.sav", "bird.movie.sav"):
        assert add[anchor]["matches_owner_census"] is True, anchor
    assert not add["conclusion_bounded"].startswith("REVIEW")


@pytest.mark.local_media
def test_save_hashes_match_disk():
    for lbl, lv in DOC["levels"].items():
        p = ROOT / lv["save"]
        assert p.exists(), f"{lbl}: {lv['save']} missing"
        h = hashlib.sha256()
        with p.open("rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        assert h.hexdigest() == lv["save_sha256"], \
            f"{lbl}: {lv['save']} changed since the census — regenerate or investigate"

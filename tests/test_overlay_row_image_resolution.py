"""The stage -> scene -> overlay-image chain, and the two parse traps it fell into.

The resolver answers "which blob does THIS row's citation of this overlay VA live in?"
using the game's own progression table rather than the artifact being resolved. These
tests pin the chain against resolutions that were established by completely independent
routes, and pin the two scope-parsing bugs that a substring test introduced.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_overlay_row_image_resolver as R  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_overlay_row_image_resolution.json"


@pytest.fixture(scope="module")
def table():
    return R.progression_table()


@pytest.fixture(scope="module")
def doc():
    if not ARTIFACT.exists():
        pytest.skip("resolution artifact not generated")
    return json.loads(ARTIFACT.read_text())


def test_progression_table_is_read_from_the_image_not_typed(table):
    assert len(table) == 16
    assert len(set(table)) == 16, "stage->scene must be injective"
    assert table[0] == 17 and table[9] == 14 and table[11] == 12


@pytest.mark.parametrize("scene,image", [
    (7, "LEVEL07_LEVEL"),    # <=10 -> LEVEL.BIN in that dir
    (10, "LEVEL10_LEVEL"),   # boundary, still LEVEL.BIN
    (12, "LEVEL02_LEVEL1"),  # >10 -> dir scene-10, LEVEL1.BIN
    (17, "LEVEL07_LEVEL1"),
])
def test_scene_to_blob_law(scene, image):
    assert R.scene_to_image(scene) == image


def test_every_known_positive_reproduces(table):
    """Each of these was established WITHOUT the progression table -- by a compiled-C byte
    probe, a 100% code-window match, a disc-side pin, or a writer-set constraint. If the
    chain stops reproducing them it is wrong, and the tool must refuse to emit."""
    reg = {r["id"]: r for r in yaml.safe_load(
        (ROOT / "analysis/mechanics_baseline.yaml").read_text())["rows"]}
    for rid, (expect, _how) in R.KNOWN_POSITIVES.items():
        ordinal, scene, _reason = R.parse_stage(reg[rid].get("stages"))
        if ordinal is not None:
            scene = table[ordinal]
        assert scene is not None, f"{rid}: stage scope failed to parse"
        assert R.scene_to_image(scene) == expect, rid


# --- the two parse traps, both caused by substring tests -------------------------

def test_prose_with_and_still_resolves_a_single_scene():
    """F10's note reads '... = 7, and the Phase-3 scene graph labels ...'. An earlier
    version rejected any prose containing ' and ' as multi-scope and silently dropped 16
    citations. The known-positive gate caught it."""
    stages = ("scene 7 (disc level07) -- derived: progression table 0x80077FA0[ordinal 10]"
              " = 7, and the Phase-3 scene graph labels scene 7 stage10_clover_forest")
    _ordinal, scene, _reason = R.parse_stage(stages)
    assert scene == 7


def test_all_inside_a_fixture_count_is_not_open_ended_scope():
    """D17 says 'confirmed for all 3 Birdnest fixtures' -- that 'all' counts fixtures, not
    stages. A substring test read it as unbounded scope and refused to narrow the row."""
    stages = ("scene 11 (chronological Level 6, Birdnest) confirmed for all 3 Birdnest "
              "fixtures; scene 6 (chronological Level 4, Cliffside Canyon) confirmed for "
              "the Cliffside fixture")
    scenes, _why = R.enumerate_scenes(stages, R.progression_table())
    assert scenes == [6, 11]


@pytest.mark.parametrize("stages", ["all", "multiple", "frontend"])
def test_whole_string_scope_words_stay_unbounded(stages, table):
    assert R.enumerate_scenes(stages, table)[0] is None


def test_scope_extending_beyond_named_stages_stays_unbounded(table):
    assert R.enumerate_scenes("Bug Bar (9) + others", table)[0] is None


def test_stage_range_enumerates_rather_than_resolving(table):
    """'stages 13-15' cannot name one image, but it does bound three."""
    assert R.parse_stage("stages 13-15")[:2] == (None, None)
    scenes, _why = R.enumerate_scenes("stages 13-15", table)
    assert scenes == [table[13], table[14], table[15]]


# --- artifact-level invariants ---------------------------------------------------

def test_no_resolution_contradicts_the_bytes(doc):
    assert doc["summary"]["falsified"] == 0
    assert doc["falsified"] == []


def test_every_resolution_is_physically_contained(doc):
    extents = {i["image"]: (int(i["file_va_base"], 16), i["size"])
               for i in json.loads((ROOT / "analysis/phase4_d3_contract.json").read_text()
                                   )["inputs"]["image_identities"]}
    for r in doc["resolved"]:
        base, size = extents[r["image"]]
        a = int(r["address"], 16)
        assert base <= a <= base + size - 4, f"{r['row']} {r['address']} vs {r['image']}"


def test_narrowing_is_a_subset_of_the_stage_scope_and_physically_contained(doc):
    """The meaningful invariant. NOT `bounded < census_candidates` -- those count
    different things (censused code vs physical containment), and comparing them is the
    category error that briefly produced 10 false falsifications."""
    extents = {i["image"]: (int(i["file_va_base"], 16), i["size"])
               for i in json.loads((ROOT / "analysis/phase4_d3_contract.json").read_text()
                                   )["inputs"]["image_identities"]}
    for r in doc["narrowed"]:
        assert set(r["bounded_images"]) <= set(r["images_from_stage_scope"]), r
        assert 1 <= r["bounded_image_count"] <= len(r["images_from_stage_scope"]), r
        a = int(r["address"], 16)
        for im in r["bounded_images"]:
            base, size = extents[im]
            assert base <= a <= base + size - 4, (r["address"], im)


def test_resolved_and_unresolved_are_disjoint_and_total(doc):
    s = doc["summary"]
    assert (s["resolved"] + s["narrowed_to_a_bounded_image_set"]
            + s["falsified"] + s["unresolved_open_ended_scope"]) == s["ambiguous_citations"]

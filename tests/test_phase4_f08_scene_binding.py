#!/usr/bin/env python3
"""Guards for the scene->asset binding correction (F08 and eleven sibling rows).

The claim being protected is that TWO DIFFERENT mechanisms are in play and must not
be conflated:

  * LEVEL DATA directory is ARITHMETIC -- dir = id <= 10 ? id : id - 10, with the
    LEVEL1.* variant for id >= 11. No table is consulted.
  * The SOUND BANK is a permuted jump table: jumptable[id-1] -> a per-scene handler
    -> a VAB prefix string in 0x8001AD0C.

Twelve rows indexed 0x8001AD0C at id-1 -- the JUMP-TABLE index -- and so quoted
another scene's sound bank. These guards fail if that conflation returns.

They also pin why it survived review twice over: `bank_index == id-1` holds for only
ids 1 and 15, and F15 is one of them, so the one row that looked right was right by
coincidence. And the correct law was already banked by Phase 3 on 2026-08-01 -- the
first version of this very artifact restated it wrongly by not reading upstream
first, which is the same failure that produced the bad rows.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "analysis/phase4_f08_scene_binding.json"
TOOL_C = ROOT / "tools/phase4_f08_scene_binding.c"
SAVE_PY = ROOT / "tools/phase4_f08_save_ram.py"
EXP = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f08_scene_asset_binding.md"

TRUE_MAP = {1: 0, 2: 2, 3: 1, 4: 6, 5: 7, 6: 3, 7: 9, 8: 13,
            9: 12, 10: 4, 11: 5, 12: 10, 13: 11, 14: 8, 15: 14, 16: 0, 17: 0}


@pytest.fixture(scope="module")
def art():
    return json.loads(ART.read_text())


def rows():
    d = yaml.safe_load((ROOT / "analysis/mechanics_baseline.yaml").read_text(
        encoding="utf-8"))
    for v in d.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            return {x["id"]: x for x in v}
    raise AssertionError("no row list")


def test_static_tool_builds_and_every_pin_holds(tmp_path):
    exe = tmp_path / "f08"
    subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-o", str(exe), str(TOOL_C)], check=True, cwd=ROOT)
    r = subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2500:]
    assert "0 failed" in r.stdout
    assert "every pin holds against the pristine image" in r.stdout


def test_the_sound_bank_map_is_recorded_in_full(art):
    got = {int(k): v for k, v in art["scene_id_to_sound_bank_index"].items()}
    assert got == TRUE_MAP


def test_level_data_directory_is_arithmetic_not_a_table(art):
    """The correction that matters: the DATA directory never comes from a table."""
    m = art["mechanism"]
    assert "ARITHMETIC" in m["level_data_directory"]
    assert "scene_id - 10" in m["level_data_directory"]
    assert "0x8003D204" in m["level_data_directory"]
    assert "0x0140" in m["level_data_directory"]
    dirs = art["scene_id_to_level_data_dir"]
    assert dirs["5"].startswith("LEVEL05/") and "LEVEL.*" in dirs["5"]
    assert dirs["17"].startswith("LEVEL07/") and "LEVEL1.*" in dirs["17"]
    assert dirs["15"].startswith("LEVEL05/") and "LEVEL1.*" in dirs["15"]


def test_the_string_is_not_the_data_path(art):
    """ids 16/17 are the proof: prefix says level01, data dirs are 6 and 7."""
    d = art["string_dir_vs_arithmetic_dir"]
    assert d["agree_for_ids"] == "1-15"
    assert "16" in d["diverge_for_ids"] and "17" in d["diverge_for_ids"]
    assert "LEVEL07_LEVEL1.BIN" in d["proof"]


def test_the_first_framing_is_recorded_as_corrected(art):
    """Phase 3 banked this law on 2026-08-01; the first version of this artifact
    restated it wrongly. Keep that admission, or the next reader repeats it."""
    prov = art["mechanism"]["provenance"]
    assert "2026-08-01" in prov
    assert "wrongly presented" in prov


def test_f08_binds_to_level05_not_level10(art):
    b = art["f08_corrected_binding"]
    assert b["scene_id"] == 5
    assert b["level_data_dir"] == "LEVEL05/" and b["variant"] == "LEVEL.*"
    assert "LEVEL05_LEVEL.BIN" in b["overlay_resident"]
    assert "JUMP-TABLE index" in b["was_claimed"]


def test_sound_bank_dispatch_stays_described_as_a_permuted_jump_table(art):
    m = art["mechanism"]
    assert "jumptable[resource_id - 1]" in m["index_form"]
    assert m["jump_table"].startswith("0x8001AFB0")
    assert "PERMUTED" in m["note"]
    assert "SOUND-BANK" in m["sound_bank"]


def test_only_two_ids_satisfy_the_bad_rule():
    coincidences = [i for i, a in TRUE_MAP.items() if a == i - 1]
    assert sorted(coincidences) == [1, 15], (
        "if this changes, the explanation for why the error survived is wrong")


def test_f15_is_flagged_as_coincidentally_correct(art):
    assert "COINCIDENCE" in art["why_it_went_unnoticed"].upper()
    assert "F15" in art["why_it_went_unnoticed"]


def test_all_eleven_wrong_rows_are_named(art):
    bad = art["rows_with_wrong_scene_asset_binding"]
    assert len(bad) == 11
    assert "F15_canyon_showdown" not in [b["row"] for b in bad]
    for b in bad:
        assert b["claimed"] != b["truth"]


def test_residency_was_confirmed_at_several_independent_scenes(art):
    conf = art["residency_confirmation"]
    assert len({c["scene"] for c in conf}) >= 4
    assert all(c["match"] for c in conf)


def test_the_false_positive_discriminator_is_recorded(art):
    """LEVEL09_LEVEL1.BIN slice-matches at a wandering base. Recording only the
    positive result would leave the next reader unable to reject it."""
    n = art["false_positive_note"]
    assert "LEVEL09" in n and "0x800B39A0" in n
    assert "wandering" in n.lower()


def test_zero_agreement_was_excluded_from_the_match(art):
    """Counting zero-vs-zero byte agreement is what made the naive number look
    convincing. The method string must keep saying it was excluded."""
    m = art["residency_method"]
    assert "zero-vs-zero" in m and "excluded" in m
    assert "99.14" in m and "5.53" in m


def test_save_extractor_refuses_an_unverified_ram_base():
    """A silently wrong base shifts every address by a constant."""
    s = SAVE_PY.read_text()
    assert "anchors did not agree" in s
    assert "Refusing rather than picking one" in s


# ------------------------------------------------------------------------ row --

def test_row_no_longer_asserts_the_level10_binding():
    """The old binding is deliberately still QUOTED, inside the falsification entry --
    that is how the next reader learns not to re-derive it. So absence of the string
    is the wrong test: what matters is that every mention sits in an entry that marks
    it false. Asserting bare absence would force the retraction to be deleted, which
    is the failure mode that once corrupted a Canon page."""
    r = rows()["F08_city_square"]
    for b in r["bindings"]:
        if "0x8001AD0C[4]" in b or "LEVEL10_LEVEL/_LEVEL1" in b:
            assert "FALSIFIED" in b, (
                "the level10 binding appears in a binding entry that does not mark "
                "it as falsified: %r" % b[:120])
    live = [b for b in r["bindings"] if "FALSIFIED" not in b]
    assert live, "the row must still carry a positive binding"
    assert any("LEVEL05/" in b and "SOUND-BANK" in b for b in live)
    assert not any("0x8001AD0C[4]" in b for b in live)


def test_every_affected_row_was_corrected(art):
    """The sweep must be complete, and D18_thud must not be forgotten -- its binding
    phrased the scene differently and was missed on the first pass."""
    corrected = art["rows_corrected"]
    assert "D18_thud" in corrected
    assert len(corrected) == 13
    allrows = rows()
    for rid in corrected:
        blob = json.dumps(allrows[rid])
        assert "SCENE ASSET BINDING CORRECTED" in blob, rid
        assert "SOUND-BANK" in blob, rid


def test_row_keeps_the_falsification_visible():
    """The corrected value alone loses the warning. The row must still say the old
    binding was wrong, so the next reader does not re-derive it."""
    blob = json.dumps(rows()["F08_city_square"])
    assert "FALSIFIED" in blob
    assert "scene id 10" in blob.lower() or "SCENE ID 10" in blob


def test_row_does_not_claim_the_objective_is_solved():
    r = rows()["F08_city_square"]
    assert "NOT found" in (r.get("missing") or "")


def test_experiment_note_records_the_first_pass_errors():
    t = " ".join(EXP.read_text().split())
    assert "What a first pass got wrong" in t
    assert "Assumed an off-by-one" in t
    assert "Nearly matched on padding" in t

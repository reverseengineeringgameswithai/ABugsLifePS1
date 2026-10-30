"""Adversarial tests for the frontier static census and its MIPS probe.

The suite deliberately includes POSITIVE CONTROLS built from hand-assembled
words.  Without them these tests would only prove that the probe is quiet, which
is also what a broken probe looks like.

Two defects are pinned permanently:

1. The delay slot.  `j TARGET / sw v0, ofs(s1)` executes the store BEFORE the
   jump transfers control, and this game registers actor handlers exactly that
   way.  Applying the jump's clobber at the jump lost every one of them.
2. Overlay address aliasing.  Twenty level overlays load at the same virtual
   address, and two of them type their first words `data` while others type the
   same words `code`, so a first-match owner search reported a pointer built
   inside LEVEL02_LEVEL1 as a LEVEL01_LEVEL function -- an image that is not
   even resident at the same time.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_frontier_static_census.py"
PROBE = ROOT / "tools/phase4_callback_probe.c"
CENSUS = ROOT / "analysis/phase4_frontier_static_census.json"
INDEX = ROOT / "analysis/phase4_static_frontier_index.json"

pytestmark = pytest.mark.skipif(not INDEX.is_file(),
                                reason="static frontier index absent")


@pytest.fixture(scope="module")
def census() -> dict:
    assert CENSUS.is_file(), "retained static census is missing"
    return json.loads(CENSUS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def probe_binary(tmp_path_factory) -> Path:
    binary = tmp_path_factory.mktemp("probe") / "phase4_callback_probe"
    subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-O2", "-Wall",
                    "-Wextra", "-Werror", str(PROBE), "-o", str(binary)],
                   check=True)
    return binary


def _words(*values: int) -> bytes:
    return b"".join(struct.pack("<I", value) for value in values)


def _run_probe(probe_binary: Path, images, windows=()) -> list[list[str]]:
    """images: [(id, base, words_bytes, [(start, end, type), ...])]"""
    with tempfile.TemporaryDirectory() as raw:
        temp = Path(raw)
        lines = [f"window\t{start:08x}\t{end:08x}" for start, end in windows]
        for image_id, base, payload, extents in images:
            path = temp / f"{image_id}.bin"
            path.write_bytes(payload)
            lines.append(f"image\t{image_id}\t{path}\t{base:08x}\t{len(payload)}")
            for start, end, kind in extents:
                lines.append(f"extent\t{image_id}\t{start:08x}\t{end:08x}\t{kind}")
        manifest = temp / "manifest.tsv"
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = subprocess.run([str(probe_binary), str(manifest)], check=True,
                                text=True, stdout=subprocess.PIPE)
    return [line.split("\t") for line in result.stdout.splitlines() if line]


# ------------------------------------------------------- positive controls --

def test_a_registration_in_a_delay_slot_is_found(probe_binary):
    """lui/addiu, then `j` with the registering `sw` in its delay slot."""
    payload = _words(
        0x3C028001,   # 80010000 lui   v0, 0x8001
        0x24420020,   # 80010004 addiu v0, v0, 0x20   -> 0x80010020
        0x08004006,   # 80010008 j     0x80010018
        0xAE220010,   # 8001000C sw    v0, 0x10(s1)   <- DELAY SLOT
        0x00000000,   # 80010010 nop
        0x00000000,   # 80010014 nop
        0x03E00008,   # 80010018 jr    ra
        0x00000000,   # 8001001C nop
        0x03E00008,   # 80010020 jr    ra    (the registered handler's entry)
        0x00000000,   # 80010024 nop
        0x00000000,   # 80010028 nop
        0x00000000,   # 8001002C nop
    )
    rows = _run_probe(probe_binary, [(
        "syn", 0x80010000, payload,
        [(0x80010000, 0x80010020, "code"), (0x80010020, 0x80010030, "code")])])
    stores = [row for row in rows if row[0] == "fnptr" and row[6] == "store"]
    assert len(stores) == 1, rows
    assert stores[0][2] == "0x80010004"      # materialised at the addiu
    assert stores[0][3] == "0x80010020"      # the registered pointer
    assert stores[0][10] == "0x8001000C"     # the consuming store
    assert stores[0][11] == "1"              # and it lands on a function entry


def test_a_registration_at_a_merge_point_is_not_claimed(probe_binary):
    """Negative control: the store sits on a branch target, so no path is proved."""
    payload = _words(
        0x14000003,   # 80020000 bne   zero, zero, 0x80020010
        0x3C028002,   # 80020004 lui   v0, 0x8002
        0x24420020,   # 80020008 addiu v0, v0, 0x20
        0x00000000,   # 8002000C nop
        0xAE220010,   # 80020010 sw    v0, 0x10(s1)   <- also a branch target
        0x03E00008,   # 80020014 jr    ra
        0x00000000,   # 80020018 nop
        0x00000000,   # 8002001C nop
        0x03E00008,   # 80020020 jr    ra    (same handler entry as the positive)
        0x00000000,   # 80020024 nop
        0x00000000,   # 80020028 nop
        0x00000000,   # 8002002C nop
    )
    rows = _run_probe(probe_binary, [(
        "syn", 0x80020000, payload,
        [(0x80020000, 0x80020020, "code"), (0x80020020, 0x80020030, "code")])])
    assert [row for row in rows if row[0] == "fnptr"] == [], (
        "the only difference from the positive control is the merge point")


def test_a_gap_reference_that_reaches_a_window_is_reported(probe_binary):
    """The gap sweep must be able to fire, or its silence proves nothing."""
    payload = _words(
        0x03E00008,   # 80030000 jr ra                  (inside the extent)
        0x00000000,   # 80030004 nop
        0x3C018008,   # 80030008 lui at, 0x8008         (gap starts here)
        0xAC2223A0,   # 8003000C sw  v0, 0x23A0(at)     -> 0x800823A0
    )
    rows = _run_probe(
        probe_binary,
        [("syn", 0x80030000, payload, [(0x80030000, 0x80030008, "code")])],
        windows=[(0x800823A0, 0x800823A2)])
    refs = [row for row in rows if row[0] == "gapref"]
    assert len(refs) == 1, rows
    assert refs[0][8] == "adjacent_lui" and refs[0][9] == "0x800823A0"
    assert refs[0][10] == "1", "a window-reaching gap reference must be flagged"


def test_a_gap_reference_with_an_unprovable_base_is_reported_undecided(probe_binary):
    payload = _words(
        0x03E00008,   # 80030000 jr ra
        0x00000000,   # 80030004 nop
        0x00000000,   # 80030008 nop                    (gap starts here)
        0xAE220010,   # 8003000C sw v0, 0x10(s1)        base never materialised
    )
    rows = _run_probe(
        probe_binary,
        [("syn", 0x80030000, payload, [(0x80030000, 0x80030008, "code")])],
        windows=[(0x800823A0, 0x800823A2)])
    refs = [row for row in rows if row[0] == "gapref"]
    assert len(refs) == 1 and refs[0][8] == "unresolved" and refs[0][10] == "0"


def test_an_aliased_overlay_address_is_not_given_to_another_image(probe_binary):
    """Two images claim 0x800B39A4; the materialising one owns its own address."""
    payload = _words(
        0x3C0B800B,   # lui  t3, 0x800b
        0x256B39A4,   # addiu t3, t3, 0x39a4   -> 0x800B39A4
        0x08000000,   # j 0x80000000 (out of image)
        0xAD6B0010,   # sw t3, 0x10(t3)        <- delay slot
    )
    images = [
        ("OVL_A", 0x800B39A0, b"\0" * 16 + payload,
         [(0x800B39A4, 0x800B39A8, "data"), (0x800B39B0, 0x800B39C0, "code")]),
        ("OVL_B", 0x800B39A0, b"\0" * 16 + payload,
         [(0x800B39A4, 0x800B39C0, "code")]),
    ]
    rows = [row for row in _run_probe(probe_binary, images) if row[0] == "fnptr"]
    for row in rows:
        assert row[1] == row[4], (
            "an overlay's own address was attributed to a different overlay: "
            f"{row}")
    # OVL_A types those bytes as data, so it must report nothing at all rather
    # than borrow OVL_B's typing.
    assert [row for row in rows if row[1] == "OVL_A"] == []


# ------------------------------------------------------- retained receipt --

def test_the_partition_arithmetic_holds_over_the_RESIDENT_universe(census):
    for image in census["image_census"]["images"]:
        # File universe and resident universe are separate, and the partition is
        # taken over the resident one. Using file_bytes here would put the
        # nonresident header back into the census as an unclassified gap.
        assert image["nonresident_prefix_bytes"] + image["resident_bytes"] == \
            image["file_bytes"]
        assert image["claimed_bytes"] + image["gap_bytes"] == image["resident_bytes"]
        assert image["overlapping_bytes"] == 0
        assert image["byte_partition_complete"] is True
        assert sum(gap["byte_count"] for gap in image["gaps"]) == image["gap_bytes"]
        for gap in image["gaps"]:
            assert int(image["resident_start"], 16) <= int(gap["start"], 16)
            assert int(gap["end"], 16) <= int(image["resident_end"], 16)


def test_the_nonresident_prefix_is_derived_from_the_bytes_not_declared(census):
    """The PS-X EXE header states its own size; the index gets it wrong."""
    images = {row["id"]: row for row in census["image_census"]["images"]}
    scus = images["SCUS_942_88"]
    assert scus["nonresident_prefix_bytes"] == 0x800
    assert scus["nonresident_prefix_source"] == "ps_x_exe_header"
    assert scus["resident_bytes"] == 468992
    assert scus["resident_start"] == "0x80010000" and scus["resident_end"] == "0x80082800"
    # This census was built because the index declared 0 here. Reporting the
    # disagreement rather than silently overriding it is what let the index be
    # corrected at source; the cross-check stays live so a future one is caught.
    assert scus["header_rule_bytes_declared_by_index"] == 0x800
    assert scus["header_rule_agrees_with_bytes"] is True
    disagreeing = [row["id"] for row in census["image_census"]["images"]
                   if not row["header_rule_agrees_with_bytes"]]
    assert disagreeing == [], disagreeing
    for row in census["image_census"]["images"]:
        if row["id"].startswith("LEVEL"):
            assert row["nonresident_prefix_bytes"] == 4
            assert row["nonresident_prefix_source"] == "index_header_rule"


def test_the_resident_partition_reconciles_with_the_gate_as_a_SET(census):
    """Two independent partitions of the SAME universe, differenced both ways.

    Once the nonresident header is out of the way the census and the gate
    partition an identical 468,992-byte range, so any difference is
    attributable to the extent source and must be named region by region.
    """
    row = census["image_census"]["resident_partition_reconciliation"]
    assert row["available"] is True
    assert row["same_resident_universe"] is True
    assert row["reconciliation"] == "exact_set_both_directions"
    # Exactly one named region on EACH side, both attributable:
    # * census-only: the 340-byte extension that was reviewed and DECLINED,
    #   which the gate's repaired extents claim and the index does not;
    # * gate-only: the 20-byte target-root island, which the gate names as its
    #   own ownership defect and deliberately leaves unclaimed, while the index
    #   promoted the decoded island to a census record on 2026-08-06. The gate
    #   receipt is untouched by contract, so this difference is expected and
    #   must stay NAMED rather than smoothed over.
    assert [(gap["start"], gap["byte_count"]) for gap in row["gate_only_gaps"]] == \
        [("0x8004C898", 20)]
    assert [(gap["start"], gap["byte_count"]) for gap in row["census_only_gaps"]] == \
        [("0x8008219C", 340)]
    assert row["identical_gaps"] == 72


def test_gap_words_are_named_for_their_ENCODING_not_asserted_as_references(census):
    """A word in unclaimed bytes that decodes as `lw` is not a memory reference.

    Counting them as undecided references states the deficit in the wrong
    category. Nothing shows any of them executes -- and no direct edge from
    reachable code enters ANY gap in ANY image.
    """
    ic = census["image_census"]
    assert "instruction_shaped_word_caveat" in ic
    for image in ic["images"]:
        assert "instruction_shaped_words_in_gaps" in image
        assert "gap_memory_references" not in image, (
            "the misleading name must not come back")


def test_the_boundary_edge_census_enumerates_EVERY_successor_kind(census):
    """"No edge enters a gap" is only a result if every edge kind was checked.

    Branch/jump/call TARGETS carry an address and were checked; two boundary
    edges do not and were invisible -- ordinary fallthrough past the end of an
    extent, and the pc+8 return continuation of a call. Both are enumerated now.
    """
    meta = census["image_census"]["gap_ownership_evidence"]
    assert set(meta["boundary_edge_kinds_enumerated"]) == {
        "fallthrough", "branch", "jump", "call", "call_return",
        "indirect_call_return", "resolved_indirect_jump"}
    assert census["verdicts"]["boundary_edges_into_gaps"] == 0
    assert census["verdicts"]["gaps_entered_by_a_direct_boundary_edge"] == 0
    for image in census["image_census"]["images"]:
        for gap in image["gap_ownership"]:
            assert gap["incoming_boundary_edge_count"] == 0


def test_ownership_is_BYTE_exact_and_never_a_whole_gap_boolean(census):
    """A gap carrying some evidence is not an owned gap.

    The previous shape marked a 13,536-byte region "has positive ownership
    evidence" on the strength of a few hundred covered bytes, leaving the rest
    unowned while the headline said otherwise.
    """
    ic = census["image_census"]
    assert "gaps_without_positive_ownership_evidence" not in ic, (
        "the whole-gap boolean must not come back")
    total = evidenced = semantic = none = 0
    for image in ic["images"]:
        for gap in image["gap_ownership"]:
            assert (gap["bytes_with_any_evidence"] + gap["bytes_with_no_evidence"]
                    == gap["byte_count"])
            assert gap["bytes_with_semantic_evidence"] <= gap["bytes_with_any_evidence"]
            assert sum(span["byte_count"] for span in gap["unevidenced_ranges"]) == \
                gap["bytes_with_no_evidence"]
            total += gap["byte_count"]
            evidenced += gap["bytes_with_any_evidence"]
            semantic += gap["bytes_with_semantic_evidence"]
            none += gap["bytes_with_no_evidence"]
    assert total == ic["total_gap_bytes"]
    assert evidenced == ic["gap_bytes_with_any_evidence"]
    assert semantic == ic["gap_bytes_with_semantic_evidence"]
    assert none == ic["gap_bytes_with_no_evidence"]
    assert evidenced + none == total
    # zero-fill says a byte holds no load/store encoding, NOT what it is, so the
    # semantic total must be far smaller than the union.
    assert semantic < evidenced


def test_every_gap_carries_an_EXPLICIT_none_partial_complete_disposition(census):
    """"Some evidence" must never be readable as "owned"."""
    ic = census["image_census"]
    assert set(ic["disposition_means"]) == {"none", "partial", "complete"}
    assert "must never be counted as one" in ic["disposition_means"]["partial"]
    counts = {"none": 0, "partial": 0, "complete": 0}
    byte_counts = {"none": 0, "partial": 0, "complete": 0}
    for image in ic["images"]:
        for gap in image["gap_ownership"]:
            disposition = gap["disposition"]
            if disposition == "none":
                assert gap["bytes_with_any_evidence"] == 0
            elif disposition == "complete":
                assert gap["bytes_with_no_evidence"] == 0
            else:
                assert gap["bytes_with_any_evidence"] > 0
                assert gap["bytes_with_no_evidence"] > 0
            counts[disposition] += 1
            byte_counts[disposition] += gap["byte_count"]
    assert counts == ic["gaps_by_disposition"]
    assert byte_counts == ic["gap_bytes_by_disposition"]
    assert counts["partial"] > 0, (
        "partial is the honest answer for most of this corpus; a corpus with no "
        "partial gaps would mean the granularity collapsed back to whole-gap")


def test_the_mover_island_is_no_longer_a_gap_because_it_is_a_census_record(census):
    """0x8004C898..0x8004C8AC left the gap universe on 2026-08-06.

    The decoded island was promoted to a first-class census record, so its 20
    bytes are CLAIMED -- not a gap carrying ownership evidence. Its two
    register-based stores moved with it: they are per-record accesses now,
    visible to the F01 ledger and the writer-census resolver, and are exactly
    the two instruction-shaped words the gap sweep stopped seeing.
    """
    for image in census["image_census"]["images"]:
        for gap in image["gap_ownership"]:
            assert not (int(gap["start"], 16) <= 0x8004C898 < int(gap["end"], 16)), (
                "the island bytes must be claimed by its census record, "
                f"but gap {gap['start']}..{gap['end']} still contains them")
    resident = next(row for row in census["image_census"]["images"]
                    if row["id"] == "SCUS_942_88")
    # The neighbouring extents did NOT widen: the byte arithmetic still closes
    # with the island as its own 20-byte extent.
    assert resident["byte_partition_complete"] is True


def test_per_class_byte_totals_are_not_exclusive_buckets(census):
    ic = census["image_census"]
    assert "must not be summed" in ic["classes_overlap"]
    assert sum(ic["gap_bytes_by_class"].values()) > ic["gap_bytes_with_any_evidence"], (
        "the classes overlap; if this ever became equality the union would be "
        "indistinguishable from the sum and the caveat would read as false")


def test_gap_ownership_classes_contribute_byte_intervals(census):
    ic = census["image_census"]
    named = set(ic["ownership_classes"])
    for image in ic["images"]:
        for gap in image["gap_ownership"]:
            assert set(gap["ownership_classes"]) <= named
            assert set(gap["bytes_by_class"]) == set(gap["ownership_classes"])
            for name, count in gap["bytes_by_class"].items():
                assert 0 < count <= gap["byte_count"], (name, count)
    assert ic["gap_bytes_with_no_evidence"] > 0, (
        "a zero here would mean every unclaimed byte has an owner, which is "
        "exactly the claim this census refuses to make for free")


def test_two_trig_gaps_move_12284_bytes_without_widening(census):
    ic = census["image_census"]
    cls = "content_verified_trigonometric_table"
    assert ic["gap_bytes_by_class"][cls] == 12284
    # Re-pinned 2026-08-07: the partial-gap campaign added three
    # gap-semantics classes (sine tail 240 B content-verified, atan table
    # 1,838 B instruction-derived extent, entry-pointer runs 172 B
    # structural after clipping). 52 B of the runs overlap bytes another
    # class already evidences, so no-evidence moves by the 2,198-byte
    # union: 11,958 -> 9,760. Derived, then pinned.
    assert ic["gap_bytes_with_no_evidence"] == 9760
    assert ic["gap_bytes_by_class"]["content_verified_trig_tail"] == 240
    assert ic["gap_bytes_by_class"]["reader_indexed_atan_table"] == 1838
    assert ic["gap_bytes_by_class"]["function_entry_pointer_run"] == 172
    assert 11958 + 12284 == 24242, "byte-exact delta from the prerequisite census"
    owned = [gap for image in ic["images"] for gap in image["gap_ownership"]
             if cls in gap["ownership_classes"]]
    assert [(gap["start"], gap["end"], gap["byte_count"])
            for gap in owned] == [
                ("0x80075930", "0x800769A8", 4216),
                ("0x8007B63C", "0x8007D5C0", 8068),
            ]
    assert all(gap["disposition"] == "complete" and
               gap["bytes_with_no_evidence"] == 0 for gap in owned)
    meta = ic["gap_ownership_evidence"][cls]
    assert meta["reader_count"] == 29
    assert meta["receipt_only_readers"] == meta["index_only_readers"] == []
    assert meta["range_or_table_mismatches"] == []
    largest = ic["largest_unevidenced_ranges"][0]
    # Re-pinned 2026-08-07: the atan-table extent evidences all but the
    # final 2 B of the former largest range (0x8007E8B8..0x8007EFE8); the
    # largest survivor is now inside the results-screen gap.
    assert largest == {"image": "SCUS_942_88", "start": "0x80078E9E",
                       "end": "0x8007913C", "byte_count": 670}
    assert census["verdicts"]["all_images_census_complete"] is False


def test_no_proved_indirect_target_lands_in_any_remaining_gap(census):
    """The island class is expected EMPTY now, and that is a property to hold.

    0x8004C898 was the specimen: a gate-proved `jr` target in unclaimed bytes,
    which analysis/phase3_jr_tables.json never decoded. Since its promotion to
    a census record, every decoded island is claimed, so a proved target
    surviving inside a gap would mean an island DECODE FAILED -- a defect to
    investigate, not ownership evidence.
    """
    for image in census["image_census"]["images"]:
        for gap in image["gap_ownership"]:
            assert "decoded_target_root_island" not in gap["ownership_classes"], (
                f"an island overlaps unclaimed gap {gap['start']}..{gap['end']}")
            assert "targeted_by_a_proved_indirect_jump" not in gap["ownership_classes"], (
                f"a proved jr target lands in gap {gap['start']}..{gap['end']} "
                "without a decoded island record")
    meta = census["image_census"]["gap_ownership_evidence"]
    # The jr universe the boundary walk was armed with is pinned, verified and
    # measured -- phase3 subset relation included -- never assumed.
    armed = meta["cfg_jr_sources_armed"]
    assert armed["phase3_jr_tables"]["verified"] is True
    assert armed["gate_only_jr_sites"]["verified"] is True
    assert armed["gate_only_jr_sites"]["phase3_sites_not_in_gate"] == []
    assert armed["phase3_jr_tables"]["artifact_sha256"]
    assert armed["gate_only_jr_sites"]["artifact_sha256"]


def test_census_complete_is_a_conjunction_not_a_partition_alone(census):
    """A complete byte partition must NOT be enough on its own."""
    incomplete = [image for image in census["image_census"]["images"]
                  if not image["census_complete"]]
    assert incomplete, "the resident image has undecided gap references"
    for image in incomplete:
        assert image["byte_partition_complete"] is True
        assert image["gap_words_all_attributed"] is False
        assert image["instruction_shaped_words_with_an_unprovable_base"] > 0
    assert census["image_census"]["census_incomplete_images"] == \
        sorted(image["id"] for image in incomplete)


def test_the_receipt_never_claims_semantic_ownership_or_bounded_pointers(census):
    assert census["function_pointer_census"]["completeness"] == "positive_only"
    assert census["function_pointer_census"]["silence_is_not_evidence"] is True
    assert census["verdicts"]["function_pointer_census_complete"] is False
    assert census["authority"] == {
        "changes_campaign_registry": False,
        "promotes_dimension": False,
        "closes_item_2": False,
        "widens_the_direct_static_writer_census": False,
    }


def test_no_gap_reference_reaches_a_window_and_the_zero_carries_its_denominator(census):
    """A hit here is a NAMED FALSIFIER for the direct static writer census.

    The zero is a bounded negative over the DECIDABLE part of the sweep, so the
    unprovable-base count must ship alongside it. Quoting the zero alone would
    read as a clean sweep of every gap byte.
    """
    verdicts = census["verdicts"]
    assert verdicts["window_reaching_gap_references"] == 0
    assert census["falsifiers"] == []
    assert verdicts["named_falsifier_found"] is False
    assert verdicts["instruction_shaped_gap_words_with_an_unprovable_base"] > 0
    assert verdicts["instruction_shaped_gap_words_total"] >= \
        verdicts["instruction_shaped_gap_words_with_an_unprovable_base"]


def test_the_receipt_states_what_census_complete_does_and_does_not_mean(census):
    text = census["image_census"]["census_complete_means"]
    assert "RESIDENT" in text
    assert "does NOT assert semantic ownership" in text.replace("\n", " ")
    assert "mechanical completeness" in text
    note = census["image_census"]["universe_note"]
    assert "nonresident_prefix_bytes" in note and "NOT as an unclassified gap" in note


def test_the_receipt_regenerates(tmp_path):
    proc = subprocess.run([sys.executable, str(TOOL), "--output", str(CENSUS),
                           "--check"], text=True, capture_output=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stderr
    assert "fresh" in proc.stdout


def test_the_receipt_pins_no_compiler_identity(census):
    """Deliberate: pinning cc's version string makes the receipt unreproducible."""
    assert "compiler" not in census["inputs"]
    assert census["inputs"]["probe_source"] == "tools/phase4_callback_probe.c"
    assert len(census["inputs"]["probe_source_sha256"]) == 64


def test_the_universe_check_compares_IDENTITY_not_just_endpoints(census):
    """Equal load endpoints do not make it the same image.

    Two different builds can occupy 0x80010000..0x80082800. If only the range
    were compared, a changed image would reconcile as "the same universe" and
    the resulting gap differences would be unattributable.
    """
    row = census["image_census"]["resident_partition_reconciliation"]
    assert row["same_resident_range"] is True
    assert row["same_image_identity"] is True
    assert row["same_resident_universe"] is (row["same_resident_range"]
                                             and row["same_image_identity"])
    assert row["gate_image_sha256"] == row["census_image_sha256"]
    assert len(row["gate_image_sha256"]) == 64
    assert row["gate_image_path"] == "REBUILD/files/SCUS_942.88"


def test_the_index_now_declares_the_resident_header_correctly(census):
    """The disagreement this census was built to expose is fixed at the source."""
    assert [row["id"] for row in census["image_census"]["images"]
            if not row["header_rule_agrees_with_bytes"]] == []
    scus = next(row for row in census["image_census"]["images"]
                if row["id"] == "SCUS_942_88")
    assert scus["header_rule_bytes_declared_by_index"] == 0x800
    # The derivation stays independent of the declaration: it still reads the
    # PS-X EXE magic rather than trusting the index, so the two can disagree
    # again and be caught.
    assert scus["nonresident_prefix_source"] == "ps_x_exe_header"


def _boundary_modules():
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_frontier_static_census as census_mod
    import phase4_static_frontier as generator
    return census_mod, generator


def test_a_delay_slot_that_is_also_an_independent_entry_keeps_its_fallthrough():
    """The delay-slot property belongs to an EXECUTION CONTEXT, not an address.

    Mutation fixture, exact sets on both arms:

    * POSITIVE: `beq zero,zero,+0` at 0x1000 branches INTO its own delay slot
      0x1004, so 0x1004 executes in two contexts -- as the delay slot (where
      the branch decides the successor) and as a branch target (where control
      continues linearly). Its fallthrough 0x1008 leaves the claimed words and
      MUST be reported. The old global address-only exclusion returned {} here;
      simulating it by withholding the independent-entry membership reproduces
      that {} exactly, which is the mutation this test exists to kill.
    * NEGATIVE: the same shape with the branch targeting its own address keeps
      0x1004 a pure delay slot, and the exact edge set stays empty.
    """
    census_mod, generator = _boundary_modules()
    assert not generator.JR_TARGETS or True  # walk below uses direct edges only

    # beq zero, zero, offset 0 -> target pc+4 = 0x1004 (unconditional)
    word_at = {0x1000: 0x10000000, 0x1004: 0x24080001}   # addiu t0, zero, 1
    reachable, block_starts, _ = generator.image_direct_cfg(word_at, [0x1000])
    assert reachable == {0x1000, 0x1004}
    assert 0x1004 in block_starts, "the branch target must be an independent entry"
    landing = census_mod.gap_boundary_edges(word_at, reachable, block_starts,
                                            generator)
    assert landing == {0x1008: [{"target": "0x00001008", "source": "0x00001004",
                                 "kind": "fallthrough"}]}

    # The MUTATION: a global address-only exclusion is exactly "no independent
    # entries", and it silently loses the edge.
    suppressed = census_mod.gap_boundary_edges(word_at, reachable, set(),
                                               generator)
    assert suppressed == {}, "the old rule must lose the edge -- if this ever "\
        "returns the edge the mutation arm no longer distinguishes the rules"

    # NEGATIVE control: branch back to itself; 0x1004 is ONLY a delay slot.
    word_at = {0x1000: 0x1000FFFF, 0x1004: 0x24080001}   # beq zero,zero,-1
    reachable, block_starts, _ = generator.image_direct_cfg(word_at, [0x1000])
    assert reachable == {0x1000, 0x1004}
    assert 0x1004 not in block_starts
    landing = census_mod.gap_boundary_edges(word_at, reachable, block_starts,
                                            generator)
    assert landing == {}


def test_the_boundary_walk_universe_is_stated_and_context_sensitive(census):
    meta = census["image_census"]["gap_ownership_evidence"]
    assert "sole established execution context" in meta["boundary_edge_universe"]
    assert "same universe as the index's CFG" in meta["boundary_edge_universe"]

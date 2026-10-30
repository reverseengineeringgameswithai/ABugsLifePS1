"""E16 item-2: the residual compiled into named boundaries, and what it costs.

DoD item 2 asks that readers/writers/consumers be ENUMERATED; the Phase-4 exit
gate asks that nothing intersect the subsystem "without being explicitly
BOUNDED"; the accepted linter consumes a hand-declared `bounded_residuals` list.
None of them asks for a machine-computed alias count of zero.

These gates pin the compiled residual, the honest discharge counts, and -- most
importantly -- the retraction of a bounding argument that looked like a 96%
discharge and was wrong.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_e16_bounded_residuals.json"


def _a():
    return json.loads(ART.read_text())


def test_the_standard_actually_applied_is_recorded():
    s = _a()["standard_applied"]
    assert "ENUMERATED" in s["dod_item_2"]
    assert "bounded, not absent" in s["exit_gate"]
    assert "bounded_residuals" in s["linter"]
    assert "appears in no standard" in s["NOT_applied"]


def test_only_the_known_consumer_can_reach_with_a_small_index():
    """The finding that makes the residual tractable: intersection is decided by
    how large an index an access would need, and only the enumerated reader needs
    a small one."""
    t = _a()["per_target"]["markers_0x30_0x57"]
    d = t["required_index_distribution"]
    assert d["<64"] == 3                      # all three are 0x8003C920, the reader
    assert t["enumerated_reader_sites"] == 3
    assert d["1k-16k"] + d[">=16k"] > 4000     # the bulk needs thousands


def test_discharge_counts_are_not_inflated():
    """Every site lands in exactly one bucket, and the two discharge BASES are
    kept apart: a cited element count is stronger evidence than the convention
    that indices are non-negative."""
    t = _a()["per_target"]["markers_0x30_0x57"]
    assert t["residual_sites"] == 4911
    assert t["bounded_by_documented_extent"] == 216
    assert t["bounded_by_proven_index_at_same_base"] == 284
    assert t["bounded_by_next_object_base"] == 536
    assert t["bounded_by_non_negative_index_convention"] == 2689
    assert t["needs_per_object_extent"] == 1183
    assert (t["enumerated_reader_sites"] + t["bounded_by_documented_extent"]
            + t["bounded_by_proven_index_at_same_base"]
            + t["bounded_by_next_object_base"]
            + t["bounded_by_non_negative_index_convention"]
            + t["needs_per_object_extent"]) == t["residual_sites"]
    assert "NOT be equivalent" in _a()["method"]["two_discharge_bases_are_NOT_equivalent"] \
        or "NOT_equivalent" in json.dumps(_a()["method"])


def test_the_priority_set_is_closed_but_the_composition_is_the_claim():
    """Closed twice now -- the first time wrongly (three refuted extents reopened
    44 sites). What makes it defensible this time is that every bound survives the
    proven-index self-check. The zero alone was never the interesting number."""
    from collections import Counter
    tot = Counter()
    for t in _a()["per_target"].values():
        sub = [b for b in t["boundaries"] if b["required_index_to_reach_target"] < 1024]
        for b in sub:
            tot[b["verdict"]] += b["sites"]
    assert sum(tot.values()) == 851
    assert tot["NEEDS_EXTENT"] == 0
    assert tot["ENUMERATED_READER"] == 7
    assert tot["BOUNDED_DOCUMENTED_EXTENT"] == 122
    assert tot["BOUNDED_NEGATIVE_INDEX"] == 722
    # closed, but 85% of it still rests on the weakest basis -- the composition is
    # the claim, not the zero.
    assert tot["BOUNDED_NEGATIVE_INDEX"] / sum(tot.values()) > 0.8


def test_a_claimed_extent_cannot_survive_being_refuted_by_the_code():
    """The mechanism, not the instance. A claimed extent smaller than a PROVEN
    (non-width-cast) index at the same base is refuted, and a refuted claim gives
    no upper bound, so it discharges nothing. The set is empty today only because
    the three claims it caught were corrected -- the check still runs."""
    src = (ROOT / "tools/phase4_e16_residual_boundaries.py").read_text()
    assert "extent_claim_REFUTED_by_proven_index" in src
    assert "A refuted claim yields NO upper bound at all" in src
    r = _a()["extent_claims_refuted_by_proven_index"]["refuted"]
    assert r == {}, r
    # and a refuted base may never be discharged on the strength of that claim
    for t in _a()["per_target"].values():
        for b in t["boundaries"]:
            if b["base"] in r:
                assert b["verdict"] != "BOUNDED_DOCUMENTED_EXTENT"


def test_the_weight_each_basis_carries_is_stated():
    """89% of the discharges rest on the non-negative-index convention -- versus
    6 of 165 in B06. A headline count would hide that."""
    w = _a()["HOW_MUCH_WEIGHT_EACH_BASIS_CARRIES"]
    assert w["non_negative_index_convention"] == 722
    assert w["documented_extent_surviving_the_self_check"] == 78
    assert w["of_the_722_resting_purely_on_the_convention"] == 526
    assert "6 of its" in w["comparison"]


def test_known_objects_has_no_duplicate_keys():
    """A duplicate dict key silently kept the OLD (extent None) entry and left 10
    sites open that were already bounded. Python takes the last one; the bug is
    invisible in review."""
    import re
    src = (ROOT / "tools/phase4_e16_residual_boundaries.py").read_text()
    block = src[src.index("KNOWN_OBJECTS = {"):src.index("def required_index")]
    keys = re.findall(r"^\s+(0x[0-9A-Fa-f]+):", block, re.M)
    assert len(keys) == len(set(keys)), [k for k in set(keys) if keys.count(k) > 1]


def test_matrix_lut_extent_is_evidenced_twice_over():
    """The tightest boundary in the set: the LUT's index is masked to 63, and its
    64 x 8 bytes end EXACTLY where E16's table begins -- bounded by one element."""
    t = _a()["per_target"]["markers_0x30_0x57"]
    lut = [b for b in t["boundaries"] if b["base"] == "0x8009B3A8"][0]
    assert lut["verdict"] == "BOUNDED_DOCUMENTED_EXTENT"
    assert "andi 0x3f" in lut["object_evidence"]
    assert "0x8009B5A8" in lut["object_evidence"]
    assert 0x8009B3A8 + 64 * 8 == 0x8009B5A8


def test_the_weld_table_lead_was_refuted_not_promoted():
    """The `slti $s2,128` lead turned out to guard a DIFFERENT table at
    0x800992A8. The bound that actually holds comes from layout: the next object
    is the matrix LUT, whose extent is independently established."""
    ev = None
    for t in _a()["per_target"].values():
        for b in t["boundaries"]:
            if b["base"] == "0x8009B2A8":
                ev = b["object_evidence"]
    assert ev and "REFUTED LEAD" in ev
    assert "0x800992A8" in ev                      # where the 128 actually applies
    assert "gp[1280]" in ev                        # the real gate
    assert "matrix LUT at 0x8009B3A8" in ev        # what does bound it


def test_the_unsound_adjacency_bound_stays_retracted():
    """It bounded each object by the distance to the nearest distinct base above
    it, discharging 4,730 of 4,911 sites. The median such distance is FOUR BYTES,
    because consecutive bases are sibling fields of one array element. A check
    that passes because it is wrong is worse than no check."""
    m = _a()["method"]
    r = m["RETRACTED_adjacency_argument"]
    assert "NOT a bounding argument" in r
    assert "4 bytes" in r and "4,730" in r
    assert "before it was banked" in r
    # and it must not be back in the verdict vocabulary
    for t in _a()["per_target"].values():
        for b in t["boundaries"]:
            assert b["extent_basis"] in (
                "documented_extent", "needs_per_object_extent",
                "extent_claim_REFUTED_by_proven_index",
                "proven_index_at_same_base", "next_object_base_within_1KB")


def test_runtime_cross_check_is_cited():
    """A static residual this large needs the runtime counter-evidence stated: a
    full boot -> frontend -> gameplay watch saw 7 PCs, none from any cluster."""
    assert "7 PCs" in _a()["method"]["runtime_cross_check"]


# ---- verification round: what survived, and what the evidence is worth ----

def test_two_of_three_refutations_were_themselves_invalid():
    """A width mask (`andi 0xff`/`0xffff`) is a C truncation, not an array bound.
    Reading it as one "proved" a 131,070-byte reach and wrongly refuted two extent
    claims. It is still a SOUND bound for exclusion -- just worthless as evidence
    of an object's size."""
    src = (ROOT / "tools/phase4_e16_residual_boundaries.py").read_text()
    assert "A WIDTH CAST is not extent evidence" in src
    assert "still SOUND for exclusion" in src
    # nothing is refuted any more
    assert _a()["extent_claims_refuted_by_proven_index"]["refuted"] == {}


def test_the_imported_claim_was_replaced_by_codebase_evidence():
    """'The SPU has 24 voices' is knowledge about the hardware, not about this
    program. _SsVmInit's literal count of 32 is."""
    a = _a()["extent_evidence_audit"]
    assert "24 voices" in a["one_claim_was_imported_from_outside_the_codebase_and_was_wrong"]
    assert "_SsVmInit" in a["one_claim_was_imported_from_outside_the_codebase_and_was_wrong"]
    assert "not evidence about" in a["one_claim_was_imported_from_outside_the_codebase_and_was_wrong"]


def test_only_two_extent_claims_are_independently_corroborated():
    """The honest state of the evidence base: 2 of 14 claims have a proven index
    at the same base agreeing with them; 12 are unverified in both directions."""
    a = _a()["extent_evidence_audit"]
    assert len(a["corroborated_by_a_proven_index"]) == 2
    assert a["no_independent_check_available"] == 12


def test_the_convention_is_declared_as_ONE_residual_not_722_findings():
    """722 line items read like 722 findings; it is one assumption, declared once.
    It now asserts non-intersection -- on MAGNITUDE, measured, not on the raw
    signed fraction -- and its named exception class is resolved."""
    r = _a()["the_non_negative_index_convention_as_ONE_named_residual"]
    assert "NEGATIVE index" in r["boundary"]
    assert "TIER 2" in r["evidence"]
    assert "ZERO need a small" in r["evidence"]
    assert "campaign" in r["next_experiment"]
    assert r["intersects_dimension"] is False
    assert "not among the sites" in r["known_exception_class_RESOLVED"]



# ---- overlay census (analysis/phase4_e16_overlay_census.json) ----

OV = ROOT / "analysis/phase4_e16_overlay_census.json"


def test_overlay_gap_is_closed_and_added_no_new_unknowns():
    """Every prior E16 residual number was RESIDENT-ONLY -- the census tool reads
    functions_resident.txt and nothing else, so overlay code had never been
    region-censused. 19 of 22 images have zero priority sites, and the 36 in the
    other three reduce to two objects, both already known."""
    o = json.loads(OV.read_text())
    assert o["images"] == 22
    assert o["total_overlay_sites_needing_index_under_1k"] == 36
    hot = {n: v["priority_sites_needing_index_under_1k"]
           for n, v in o["per_image"].items()
           if v.get("priority_sites_needing_index_under_1k")}
    assert set(hot) == {"LEVEL08/LEVEL1.BIN", "LEVEL09/LEVEL.BIN", "BITS/MEMORY.BIN"}
    bases = {e["base"] for v in o["per_image"].values() for e in v.get("examples", [])}
    assert bases <= {"0x8009B878", "0x800A6300"}      # no NEW objects


def test_overlay_reachability_is_not_the_tautology():
    """Asking whether an unbounded index CAN reach a window flagged 714 of 958
    sites, every one unbounded. Required-index magnitude is what discriminates."""
    o = json.loads(OV.read_text())
    assert "tautology" in o["why_not_could_reach"]
    assert "714 of 958" in o["why_not_could_reach"]


def test_the_next_object_bound_is_constrained_not_tautological():
    """Unconstrained, clustering discharges 100% of the residual -- the tautology
    signature. Its tight-margin cases are exactly those where NO neighbour was
    seen for 12-18 KB, so the "extent" is a gap. It is accepted only where a real
    neighbour sits within 1 KB AND the required distance exceeds it 10-fold."""
    r = _a()["the_next_object_bound_as_ONE_named_residual"]
    assert "100% of the" in r["evidence"] and "tautology signature" in r["evidence"]
    assert "sibling FIELDS" in r["evidence"]      # why the naive version was retracted
    assert "within 1 KB AND a 10x margin" in r["evidence"]
    assert r["intersects_dimension"] is False


def test_the_blocker_shrank_but_did_not_close():
    """Four bases now discharge; the >=1k remainder fell 7,938 -> 4,166 and is
    still the single thing blocking the packet."""
    from collections import Counter
    t = Counter()
    for v in _a()["per_target"].values():
        for b in v["boundaries"]:
            t[b["verdict"]] += b["sites"]
    assert t["NEEDS_EXTENT"] == 4166
    assert t["BOUNDED_PROVEN_INDEX"] == 886
    assert t["BOUNDED_NEXT_OBJECT"] == 2652

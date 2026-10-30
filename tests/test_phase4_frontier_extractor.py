"""Adversarial tests for the semantic-frontier extractor.

Every test here pins a defect the extractor actually shipped with, or a silent
narrowing it must never reintroduce. They are deliberately hostile: each one
should fail loudly if the corresponding guarantee regresses.

The four defects these lock down:

1. Address-keyed identity. 16 entry addresses in the static index are shared by
   more than one overlay -- every level overlay entry sits at 0x800B39A4 -- so an
   address-keyed map discarded 42 of 1,190 records and hid 3 real accesses into
   the F01 windows.
2. Callers declared but never reached. The checker only credits
   consumer_categories for functions its walk reaches, so callers that were not
   roots contributed nothing and left the `callers` category empty.
3. Silently dropped edges and accesses. Call edges outside the closure were
   `continue`d away, and unresolved accesses vanished, so the emitted query
   looked more complete than the evidence.
4. `index: null` in an access expression reads as an UNBOUNDED domain, which made
   every access "unknown" instead of decidable.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_frontier_extractor.py"
SEED = ROOT / "config/phase4_f01_frontier_seed.yaml"
QUERY = ROOT / "config/phase4_f01_frontier_query.yaml"
SUMMARY = ROOT / "analysis/phase4_f01_frontier_extraction.json"
BLOCKERS = ROOT / "analysis/phase4_f01_frontier_blockers.json"
INDEX = ROOT / "analysis/phase4_static_frontier_index.json"

pytestmark = pytest.mark.skipif(not INDEX.is_file(), reason="static frontier index absent")


@pytest.fixture
def repo_tmp():
    """Scratch INSIDE the repository: the tool refuses to write outside it."""
    path = ROOT / f"analysis/.frontier_extractor_test_{os.getpid()}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="module")
def retained() -> tuple[dict, dict]:
    assert QUERY.is_file() and SUMMARY.is_file(), "retained extractor outputs are missing"
    return (yaml.safe_load(QUERY.read_text(encoding="utf-8")),
            json.loads(SUMMARY.read_text(encoding="utf-8")))


# ------------------------- discoveries from the adversarial review (round 2) --

def test_every_whole_universe_resolved_hit_is_emitted(retained):
    """The silent narrowing that survived round 1.

    Accesses were scanned only inside the selected closure, so 17 statically
    RESOLVED intersecting accesses -- including the timer decrementer 0x800553F8,
    observed 68 times at runtime -- never reached the query and were not even
    listed as blockers. Reachability from a chosen root has nothing to do with
    whether code touches the window.
    """
    query, summary = retained
    index = json.loads(INDEX.read_text())
    windows = [(w["start"], w["end"]) for w in query["windows"]]
    gp = 0x80081D98

    def resolve(access):
        if access.get("address"):
            try:
                return int(str(access["address"]), 16)
            except ValueError:
                return None
        if access.get("base_register") == "gp":
            return (gp + int(access.get("offset", 0))) & 0xFFFFFFFF
        return None

    universe = 0
    for record in index["records"]:
        if not record.get("entry"):
            continue
        for access in record.get("memory_accesses") or []:
            effective = resolve(access)
            if effective is not None and any(lo <= effective < hi for lo, hi in windows):
                universe += 1
    assert universe > 0
    # The index is only ONE source. Emitted must be the UNION of the index's
    # CFG-reachable accesses and the independent binary scan, and must never be
    # fewer than either.
    assert len(query["accesses"]) >= universe
    assert summary["accesses_from_static_index"] == universe
    assert summary["whole_universe_accesses_not_emitted"] == 0
    assert (summary["accesses_from_static_index"]
            + summary["accesses_from_binary_supplement"]
            == summary["accesses_emitted_from_selected"])
    # ⚠️ `accesses_from_binary_supplement` is now ZERO, and that is a RESULT, not a
    # regression: once the index's CFG recovery became the whole-image direct-edge
    # fixed point it found all nine of the accesses the supplement used to be the
    # sole source of, so the two independent methods -- constant propagation over a
    # recovered CFG, and a linear adjacent-lui scan of every word -- now agree on
    # all 124 with no residue either way.
    #
    # Asserting `> 0` here would now fail for the RIGHT reason, so it is replaced
    # rather than relaxed: what must never regress is that the supplement is still
    # CONSULTED and still independently proves the nine. That is asserted directly
    # against the bytes in test_the_nine_are_found_independently_of_the_static_index,
    # which does not consult the index at all.
    assert "accesses_from_binary_supplement" in summary
    assert summary["accesses_from_binary_supplement"] == 0, (
        "the supplement finding something again means the index's CFG recovery "
        "has regressed, or a new window access exists that only the linear scan "
        "can see -- either way, investigate before changing this number")


# The golden regression: nine F01 accesses the static index never saw, because
# it recovered only 8 of scene_flow_dispatcher's 393 instructions. Every one is
# independently confirmed by runtime evidence and Canon. They must be present
# WITHOUT depending on the index's CFG recovery.
NINE_OMITTED_PCS = [0x8004FE44, 0x8004FE4C, 0x8004FEF0, 0x8004FF04, 0x8004FF28,
                    0x8004FF90, 0x800500A8, 0x800501AC, 0x80050220]


def test_the_nine_index_invisible_accesses_are_present(retained):
    query, _ = retained
    emitted = {a["pc"] for a in query["accesses"]}
    missing = [f"{pc:#010x}" for pc in NINE_OMITTED_PCS if pc not in emitted]
    assert not missing, f"index-invisible F01 accesses absent from the frontier: {missing}"


def test_the_nine_are_found_independently_of_the_static_index():
    """Prove the golden set comes from the binaries, not from the index."""
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_frontier_extractor as extractor
    proven = extractor.binary_supplement(
        ROOT / "REBUILD" / "files" / "SCUS_942.88", 0x80010000, 0x800,
        [(0x800823A0, 0x800823A2), (0x80082470, 0x80082472)])
    found = {row["pc"] for row in proven}
    missing = [f"{pc:#010x}" for pc in NINE_OMITTED_PCS if pc not in found]
    assert not missing, f"binary scan failed to prove: {missing}"


def test_the_timer_decrementer_is_present(retained):
    """0x800553F8 is the single most important writer in the F01 story."""
    query, _ = retained
    assert any(a["pc"] == 0x800553F8 for a in query["accesses"]), \
        "the transition-timer decrementer is missing from the frontier"


def test_binary_supplement_rejects_a_clobbered_lui():
    """`lui at,X / addiu at,zero,0 / sh ...,ofs(at)` must NOT be reported proven."""
    import struct
    import tempfile
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_frontier_extractor as extractor
    windows = [(0x800823A0, 0x800823A2)]

    def scan(words):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as handle:
            handle.write(b"".join(struct.pack("<I", word) for word in words))
            path = Path(handle.name)
        try:
            return extractor.binary_supplement(path, 0x80010000, 0, windows)
        finally:
            path.unlink()

    LUI_AT, SH_AT = 0x3C018008, 0xA42023A0
    assert len(scan([LUI_AT, SH_AT])) == 1, "an adjacent lui must be proven"
    assert len(scan([0x3C028008, 0x844223A0])) == 1, \
        "the lui v0 / lh v0 idiom has rs == rt and must still resolve"
    # Adjacency is REQUIRED, so every one of these is rejected without needing a
    # model of which instructions clobber which register. jalr, mfc0 and lwl all
    # defeated the earlier clobber-tracking attempt.
    for name, filler in (("addiu", 0x24010000), ("jal", 0x0C000000), ("jalr", 0x0040F809),
                         ("mfc0", 0x40016000), ("lwl", 0x88210000), ("nop", 0x00000000)):
        assert scan([LUI_AT, filler, SH_AT]) == [], \
            f"a lui separated by {name} must not be reported as a proven base"


def test_unanalysed_extents_are_global_not_only_selected(retained):
    """An extent the index could not analyse may hold window accesses whether or
    not its function is in the closure."""
    _, summary = retained
    index = json.loads(INDEX.read_text())
    expected = sum(1 for record in index["records"]
                   if record.get("entry") and record.get("unreachable_instruction_count"))
    assert summary["mechanical_blockers"]["unanalysed_extents"]["count"] == expected
    assert any(not row["selected"]
               for row in json.loads(BLOCKERS.read_text())["unanalysed_extents"]), \
        "no unselected extent retained -- the ledger is still closure-scoped"


def test_an_arbitrary_query_cannot_reuse_the_empty_test_ledger(retained):
    """The exploit: swap in the synthetic empty ledger to claim completeness."""
    import copy
    import hashlib
    query, _ = retained
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker
    empty = ROOT / "tests/fixtures/frontier_empty_ledger.json"
    tampered = copy.deepcopy(query)
    tampered["mechanical_completeness"].update(
        complete=True, retained_blockers=0,
        ledger_path="tests/fixtures/frontier_empty_ledger.json",
        ledger_sha256=hashlib.sha256(empty.read_bytes()).hexdigest())
    with pytest.raises(checker.FrontierError):
        checker.validate_query(tampered)


def test_the_attestation_cannot_be_lifted_onto_another_query(retained):
    import copy
    query, _ = retained
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker
    tampered = copy.deepcopy(query)
    tampered["windows"][0]["end"] += 0x100
    with pytest.raises(checker.FrontierError, match="query_digest"):
        checker.validate_query(tampered)


def test_summary_binds_the_final_query_bytes_exactly(retained):
    import hashlib
    _, summary = retained
    assert summary["query_sha256"] == hashlib.sha256(QUERY.read_bytes()).hexdigest()


def test_provenance_requires_regeneration_not_a_recomputable_hash(retained):
    """query_digest is a public hash anyone can recompute, so it cannot prove
    provenance. Only re-running the extractor can."""
    import copy
    import hashlib
    query, _ = retained
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker

    def rebind(document):
        stripped = {k: v for k, v in document.items() if k != "mechanical_completeness"}
        stripped["mechanical_completeness"] = {
            k: v for k, v in document["mechanical_completeness"].items() if k != "attested_by"}
        document["mechanical_completeness"]["attested_by"]["query_digest"] = \
            hashlib.sha256(checker.canonical_json(stripped)).hexdigest()
        return document

    forged = rebind(copy.deepcopy(query))
    forged["target"]["id"] = "forged"
    forged["windows"][0]["end"] += 0x100
    empty = ROOT / "tests/fixtures/frontier_empty_ledger.json"
    forged["mechanical_completeness"].update(
        complete=True, retained_blockers=0,
        ledger_path="tests/fixtures/frontier_empty_ledger.json",
        ledger_sha256=hashlib.sha256(empty.read_bytes()).hexdigest())
    rebind(forged)
    checker.validate_query(forged)            # structurally legal by construction
    provenance = checker.verify_provenance(forged)
    assert provenance["verified"] is False
    report = checker.compile_frontier(forged)
    assert report["verdicts"]["item2_ready_for_review"] is False
    assert report["verdicts"]["strict_frontier_closed"] is False
    assert "PROVENANCE_UNVERIFIED" in report["verdicts"]["review_blockers"]


def test_a_hash_correct_noop_attester_is_refused(retained, repo_tmp):
    """The trust root must be the CHECKER's, not the document's.

    Hashing a document-chosen file only proves which file ran. A repo-relative
    no-op that exits zero would otherwise "reproduce" anything -- and did, before
    this gate: it granted strict_frontier_closed and item2_ready even though the
    declared summary did not exist.
    """
    import copy
    import hashlib
    query, _ = retained
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker

    noop = repo_tmp / "noop_attester.py"
    noop.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    relative = str(noop.resolve().relative_to(ROOT))

    forged = copy.deepcopy(query)
    forged["mechanical_completeness"]["attested_by"].update(
        tool=relative,
        tool_sha256=hashlib.sha256(noop.read_bytes()).hexdigest())

    # It must not even validate: the trust root is checked structurally, so
    # compile_frontier (which re-validates) can never reach a verdict for it.
    with pytest.raises(checker.FrontierError, match="checker-trusted"):
        checker.validate_query(forged)
    with pytest.raises(checker.FrontierError, match="checker-trusted"):
        checker.compile_frontier(forged)
    # And provenance refuses it independently of validation.
    provenance = checker.verify_provenance(forged)
    assert provenance["verified"] is False
    assert "untrusted attesting tool" in provenance["detail"]


def test_compile_frontier_owns_provenance_and_accepts_no_claim(retained):
    """The exact-method spoof.

    While provenance was a parameter, {"verified": True, "method": "regeneration"}
    bought strict_frontier_closed and item2_ready outright -- "regeneration" is a
    public string, not proof, so checking it only made the assertion more
    specific. The compiler now verifies provenance itself and takes no such
    parameter at all.
    """
    import inspect
    query, _ = retained
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker

    signature = inspect.signature(checker.compile_frontier)
    assert list(signature.parameters) == ["document"], \
        "compile_frontier must not accept caller-supplied provenance"
    with pytest.raises(TypeError):
        checker.compile_frontier(
            query, {"verified": True, "method": "regeneration", "detail": "hand asserted"})


def test_the_trusted_extractor_list_is_owned_by_the_checker():
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker
    assert checker.TRUSTED_EXTRACTORS == ("tools/phase4_frontier_extractor.py",)
    assert checker.PROVENANCE_METHOD == "regeneration"


def test_a_hand_built_document_can_never_be_ready(retained):
    """A document that is not the attested query file cannot reach a verdict of
    ready, however its own fields are set."""
    import copy
    query, _ = retained
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker
    import hashlib
    forged = copy.deepcopy(query)
    forged["target"]["scope_statement"] += " (edited)"
    # An un-rebound edit is refused outright by the digest.
    with pytest.raises(checker.FrontierError, match="query_digest"):
        checker.compile_frontier(forged)
    # A digest-consistent forgery validates, and still cannot be ready: it is not
    # the attested query file, so regeneration refuses it.
    stripped = {k: v for k, v in forged.items() if k != "mechanical_completeness"}
    stripped["mechanical_completeness"] = {
        k: v for k, v in forged["mechanical_completeness"].items() if k != "attested_by"}
    forged["mechanical_completeness"]["attested_by"]["query_digest"] = \
        hashlib.sha256(checker.canonical_json(stripped)).hexdigest()
    report = checker.compile_frontier(forged)
    assert report["provenance"]["verified"] is False
    assert report["verdicts"]["item2_ready_for_review"] is False
    assert "PROVENANCE_UNVERIFIED" in report["verdicts"]["review_blockers"]


def test_the_retained_f01_query_does_verify(retained):
    query, _ = retained
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker
    provenance = checker.verify_provenance(query)
    assert provenance["verified"] is True, provenance["detail"]
    assert provenance["method"] == "regeneration"


def test_control_flow_gaps_are_accounted_not_solved(retained):
    """Jump edges and unanalysed extents are RETAINED, not silently ignored."""
    _, summary = retained
    blockers = summary["mechanical_blockers"]
    for key in ("direct_jumps_out", "indirect_jumps", "incoming_jumps", "unanalysed_extents"):
        assert key in blockers, f"{key} is not accounted for at all"
    assert blockers["unanalysed_extents"]["count"] > 0, \
        "scene_flow_dispatcher alone has 385 unreachable instructions"


def test_omitted_incoming_callers_are_recorded(retained):
    _, summary = retained
    entry = summary["mechanical_blockers"]["omitted_incoming_callers"]
    assert entry["count"] > 0, "the caller surface is one layer deep; the next layer must be kept"
    assert entry["sample"], "omitted incoming callers recorded without detail"


def test_blocker_ledger_is_complete_and_hash_bound(retained):
    """The summary keeps a sample; the ledger must keep every entry with a stable id."""
    import hashlib
    _, summary = retained
    ledger = json.loads(BLOCKERS.read_text())
    binding = summary["blockers_ledger"]
    assert binding["sha256"] == hashlib.sha256(BLOCKERS.read_bytes()).hexdigest()
    total = sum(len(v) for v in ledger.values() if isinstance(v, list))
    assert total == sum(e["count"] for e in summary["mechanical_blockers"].values())
    for key, value in ledger.items():
        if isinstance(value, list):
            for row in value:
                assert row.get("id"), f"{key} entry without a stable id"


def test_checker_readiness_is_impossible_while_mechanically_incomplete(retained):
    """mechanical_completeness is a HARD checker input, not advisory prose."""
    import copy
    query, _ = retained
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker
    assert query["mechanical_completeness"]["complete"] is False
    result = json.loads((ROOT / "analysis/phase4_f01_frontier_result.json").read_text())
    assert "MECHANICALLY_INCOMPLETE" in result["verdicts"]["review_blockers"]
    assert result["verdicts"]["item2_ready_for_review"] is False
    for mutation in ({"complete": True},
                     {"complete": True, "retained_blockers": 0},
                     {"retained_blockers": 0},
                     {"ledger_sha256": "0" * 64},
                     {"ledger_path": "../escape.json"}):
        tampered = copy.deepcopy(query)
        tampered["mechanical_completeness"].update(mutation)
        with pytest.raises(checker.FrontierError):
            checker.validate_query(tampered)


def _run(*args: str, expect_ok: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, cwd=ROOT)
    if expect_ok:
        assert proc.returncode == 0, proc.stderr or proc.stdout
    return proc


# --------------------------------------------------------- identity (item 1) --

def test_overlay_collisions_actually_exist_in_the_index():
    """The premise: without this, address-keyed identity would be harmless."""
    index = json.loads(INDEX.read_text())
    by_address: dict[str, set[str]] = {}
    for record in index["records"]:
        if record.get("entry"):
            by_address.setdefault(record["entry"].lower(), set()).add(record["image_id"])
    shared = {a: i for a, i in by_address.items() if len(i) > 1}
    assert shared, "expected overlay entry-address collisions in the index"
    assert len(shared) >= 16


def test_function_ids_are_image_qualified_and_unique(retained):
    query, _ = retained
    ids = [f["id"] for f in query["functions"]]
    assert len(ids) == len(set(ids)), "duplicate function ids"
    for function in query["functions"]:
        assert function["id"].startswith(function["image"] + ":"), function["id"]


def test_a_colliding_address_is_not_collapsed_across_images(retained):
    """0x800B39A4 exists in many overlays; each must keep its own identity."""
    query, _ = retained
    entries = [f for f in query["functions"] if f["start"] == 0x800B39A4]
    images = {f["image"] for f in entries}
    if entries:
        assert len(entries) == len(images), "one colliding address collapsed across images"


def test_every_edge_target_names_a_declared_function(retained):
    query, _ = retained
    declared = {f["id"] for f in query["functions"]}
    for function in query["functions"]:
        for edge in function["direct_calls"]:
            assert edge["target"] in declared, f"{function['id']} -> {edge['target']}"


def test_seed_rejects_a_bare_address_root(repo_tmp):
    seed = yaml.safe_load(SEED.read_text(encoding="utf-8"))
    seed["roots"] = ["0x80048138"]
    bad = repo_tmp / "seed.yaml"
    bad.write_text(yaml.safe_dump(seed), encoding="utf-8")
    proc = _run(str(bad), "--output", str(repo_tmp / "q.yaml"),
                "--summary", str(repo_tmp / "s.json"),
                "--blockers", str(repo_tmp / "b.json"), expect_ok=False)
    assert proc.returncode != 0
    assert "ambiguous across overlays" in (proc.stderr + proc.stdout)


# ---------------------------------------------------------- callers (item 2) --

def test_callers_are_emitted_as_roots(retained):
    query, summary = retained
    assert summary["functions_added_as_callers"] > 0
    caller_ids = {f["id"] for f in query["functions"]
                  if f["consumer_categories"] == ["callers"]}
    assert caller_ids, "no function was classified as a caller"
    assert caller_ids <= set(query["roots"]), \
        "callers must be roots or the checker never reaches them"


def test_every_declared_function_is_a_root(retained):
    query, _ = retained
    assert set(query["roots"]) == {f["id"] for f in query["functions"]}


# ------------------------------------------------- mechanical blockers (3) ----

def test_blockers_are_preserved_not_dropped(retained):
    _, summary = retained
    blockers = summary["mechanical_blockers"]
    for key in ("omitted_direct_edges", "unresolvable_direct_edges", "unresolved_accesses"):
        assert key in blockers
        assert isinstance(blockers[key]["count"], int)
    assert blockers["omitted_direct_edges"]["count"] > 0, \
        "the F01 closure omits real edges; they must be recorded, not silently skipped"
    assert blockers["omitted_direct_edges"]["sample"], "omitted edges recorded without a sample"


def test_mechanically_complete_is_false_while_blockers_exist(retained):
    _, summary = retained
    blockers = summary["mechanical_blockers"]
    any_blocker = any(entry["count"] for entry in blockers.values())
    assert summary["mechanically_complete"] is not any_blocker
    if any_blocker:
        assert summary["mechanically_complete"] is False
        assert "understate the frontier" in summary["completeness_warning"]


def test_unresolved_accesses_are_split_by_base_register(retained):
    _, summary = retained
    unresolved = summary["mechanical_blockers"]["unresolved_accesses"]
    assert unresolved["count"] == unresolved["stack_relative"] + unresolved["non_stack"]
    assert unresolved["by_base_register"], "unresolved accesses must be attributed"


def test_indirect_tables_are_emitted_incomplete(retained):
    query, _ = retained
    for table in query["indirect_tables"]:
        assert table["complete"] is False, \
            "an unenumerated indirect target set must never be emitted complete"


# ------------------------------------------------------- determinism (item 4) --

def test_summary_binds_seed_and_index_hashes(retained):
    import hashlib
    _, summary = retained
    assert summary["source_seed_sha256"] == hashlib.sha256(SEED.read_bytes()).hexdigest()
    assert summary["source_index_sha256"] == hashlib.sha256(INDEX.read_bytes()).hexdigest()
    # query_sha256 pins the query as rendered BEFORE the ledger hash is folded in,
    # so it is a provenance stamp of the extraction, not of the retained file.
    assert len(summary["query_sha256"]) == 64
    assert summary["blockers_ledger"]["sha256"] == hashlib.sha256(BLOCKERS.read_bytes()).hexdigest()


def test_check_accepts_retained_outputs():
    proc = _run(str(SEED), "--output", str(QUERY), "--summary", str(SUMMARY),
                "--blockers", str(BLOCKERS), "--check")
    assert "fresh" in proc.stdout


def test_check_rejects_a_stale_output(repo_tmp):
    stale_query = repo_tmp / "q.yaml"
    stale_summary = repo_tmp / "s.json"
    stale_query.write_text("schema: tampered\n", encoding="utf-8")
    stale_summary.write_text("{}\n", encoding="utf-8")
    proc = _run(str(SEED), "--output", str(stale_query), "--summary", str(stale_summary),
                "--blockers", str(repo_tmp / "b.json"), "--check", expect_ok=False)
    assert proc.returncode != 0
    assert "stale" in (proc.stderr + proc.stdout)


def test_outputs_must_stay_inside_the_repository(repo_tmp):
    proc = _run(str(SEED), "--output", "/tmp/escape.yaml",
                "--summary", str(repo_tmp / "s.json"),
                "--blockers", str(repo_tmp / "b.json"), expect_ok=False)
    assert proc.returncode != 0
    assert "inside the repository" in (proc.stderr + proc.stdout)


# ------------------------------------------------- unbounded-domain regression --

def test_no_access_is_emitted_with_a_null_index(retained):
    """index=null reads as an unbounded domain and makes every access unknown."""
    query, _ = retained
    for access in query["accesses"]:
        index = access["expression"]["index"]
        assert index is not None, f"{access['id']} would be an unbounded domain"
        assert index["maximum_exclusive"] > index["minimum"]


def test_emitted_query_passes_the_checker_validator(retained):
    query, _ = retained
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker
    checker.validate_query(query)


def test_authority_matches_the_non_promotion_contract(retained):
    query, _ = retained
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_semantic_frontier as checker
    assert query["authority"] == checker.AUTHORITY
    assert query["authority"]["promotes_dimension"] is False
    assert query["authority"]["unknown_is_disjoint"] is False


# ------------------------------------------- derived surfaces (2026-08-06) --
# Every test below pins a defect the retained F01 query actually shipped with:
# a boundary owner and two residuals keyed by strings no emitted identity could
# ever equal, and a per-image census flag the seed simply asserted.

CENSUS = ROOT / "analysis/phase4_frontier_static_census.json"
GATE = ROOT / "analysis/phase4_static_asm_prerequisites.json"


def _seed_variant(repo_tmp, mutate):
    seed = yaml.safe_load(SEED.read_text(encoding="utf-8"))
    mutate(seed)
    path = repo_tmp / "seed.yaml"
    path.write_text(yaml.safe_dump(seed), encoding="utf-8")
    return _run(str(path), "--output", str(repo_tmp / "q.yaml"),
                "--summary", str(repo_tmp / "s.json"),
                "--blockers", str(repo_tmp / "b.json"), expect_ok=False)


def test_a_boundary_owner_naming_no_emitted_edge_is_refused(repo_tmp):
    """The exact shape the retained seed carried: an owner keyed by a category."""
    def mutate(seed):
        seed["boundary_owners"] = [{
            "edge": "unresolved_register_based_accesses",
            "owner": "someone", "reason": "because", "evidence": "none"}]
    proc = _seed_variant(repo_tmp, mutate)
    assert proc.returncode != 0
    assert "boundary_owners name edges this query does not emit" in (
        proc.stderr + proc.stdout)


def test_a_residual_covering_nothing_is_refused(repo_tmp):
    def mutate(seed):
        seed["residuals"][0]["covers"] = ["unknown_accesses"]
    proc = _seed_variant(repo_tmp, mutate)
    assert proc.returncode != 0
    assert "covers nothing" in (proc.stderr + proc.stdout)


def test_a_hand_typed_covered_ids_list_cannot_replace_the_rule(repo_tmp):
    def mutate(seed):
        for residual in seed["residuals"]:
            residual.pop("covers", None)
            residual["covered_ids"] = ["indirect_call_targets_unenumerated"]
    proc = _seed_variant(repo_tmp, mutate)
    assert proc.returncode != 0
    assert "must declare a non-empty `covers` rule" in (proc.stderr + proc.stdout)


def test_dropping_a_covers_rule_leaves_unknowns_uncovered_and_fails_closed(repo_tmp):
    """Coverage is reconciled as a SET: a rule that goes short cannot pass."""
    def mutate(seed):
        seed["residuals"] = [seed["residuals"][0]]
    proc = _seed_variant(repo_tmp, mutate)
    assert proc.returncode != 0
    assert "covered by no residual" in (proc.stderr + proc.stdout)


def test_every_emitted_unknown_is_covered_exactly_once(retained):
    query, _ = retained
    unknowns = set()
    tables = {row["id"]: row for row in query["indirect_tables"]}
    for function in query["functions"]:
        for edge in function["indirect_calls"]:
            if not tables[edge["table"]]["complete"]:
                unknowns.add(f"{function['id']}@0x{edge['site']:08X}->{edge['table']}")
    for group in query["callbacks"]:
        if not group["complete"]:
            unknowns.add(f"callback:{group['id']}")
    covered = [identity for residual in query["residuals"]
               for identity in residual["covered_ids"]]
    assert unknowns, "the query must still emit unknowns; a silent zero is not closure"
    assert sorted(covered) == sorted(unknowns)
    assert len(covered) == len(set(covered)), "an unknown is covered twice"


def test_callbacks_are_derived_incomplete_and_land_on_declared_functions(retained):
    query, summary = retained
    declared = {row["id"] for row in query["functions"]}
    assert query["callbacks"], "the callback surface must be enumerated, not empty"
    assert summary["callback_groups_emitted_incomplete"] == len(query["callbacks"])
    for group in query["callbacks"]:
        assert group["complete"] is False, (
            "a positive-only census may enumerate registration SITES but must never "
            "claim a bounded target SET")
        assert group["targets"], "a callback group with no target decides nothing"
        for target in group["targets"]:
            assert target in declared


def test_the_delay_slot_registration_is_found(retained):
    """Regression pin for the bug that cost this census a third of its findings.

    `j 0x8004a620 / sw v0,116(s1)` registers an actor handler IN THE DELAY SLOT,
    which runs before the jump takes effect. Applying the jump's clobber at the
    jump loses every one of them.
    """
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    stores = {row["consumer_pc"] for row in census["function_pointer_census"]["sites"]
              if row["consumer"] == "store"}
    assert "0x8004A570" in stores
    assert {"0x8004A588", "0x8004A5A0", "0x8004A5C8", "0x8004A5D8"} <= stores


def test_every_retained_function_pointer_lands_on_a_function_entry():
    """Noise would land at random offsets; every kept site lands on an entry."""
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    sites = census["function_pointer_census"]["sites"]
    assert sites
    assert all(row["target_is_function_entry"] for row in sites)
    assert all(row["value"] == row["target_function"] for row in sites)


def test_an_overlay_pointer_is_never_attributed_to_another_overlay():
    """Twenty overlays share one load address; first-match ownership is wrong."""
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    for row in (census["function_pointer_census"]["sites"] +
                census["function_pointer_census"]["excluded_interior_code_addresses"]):
        if row["image"].startswith("LEVEL"):
            assert row["target_image"] in (row["image"], "SCUS_942_88", "-",
                                           "*ambiguous*"), row


def test_census_completeness_is_derived_not_declared(repo_tmp, retained):
    query, summary = retained
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    derived = {row["id"]: row["census_complete"]
               for row in census["image_census"]["images"]}
    for image in query["universe"]["images"]:
        assert image["census_complete"] is derived[image["id"]]
    assert summary["images_census_incomplete"], (
        "two images are undecided; a green census here would be the finding, not "
        "the default")

    def mutate(seed):
        seed["census_complete"] = {row["id"]: True for row in
                                   query["universe"]["images"]}
    proc = _seed_variant(repo_tmp, mutate)
    assert proc.returncode != 0
    assert "no longer accepted" in (proc.stderr + proc.stdout)


def test_a_receipt_cannot_drift_underneath_its_pin(repo_tmp):
    def mutate(seed):
        seed["evidence_receipts"]["static_census"]["sha256"] = "0" * 64
    proc = _seed_variant(repo_tmp, mutate)
    assert proc.returncode != 0
    assert "does not match" in (proc.stderr + proc.stdout)


def test_indirect_sites_reconcile_with_the_gate_as_a_SET_not_a_COUNT(retained):
    _, summary = retained
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    row = summary["indirect_control_reconciliation"]
    assert row["reconciliation"] == "exact_set_both_directions"
    assert row["resident_indirect_call_sites_absent_from_gate"] == []
    assert row["resident_indirect_jump_sites_absent_from_gate"] == []
    assert row["gate_typed_candidate_sites"] == 235
    assert (row["gate_jr_sites"] + row["gate_jalr_sites"] ==
            row["gate_typed_candidate_sites"])
    inventory = gate["indirect_control"]
    assert len(inventory["jr_sites"]) == row["gate_jr_sites"]
    assert len(inventory["jalr_sites"]) == row["gate_jalr_sites"]
    # What the gate decides here, measured: every resident indirect JUMP, and no
    # indirect CALL. Equal aggregate counts on both sides would hide this.
    assert row["ledger_jump_sites_with_a_gate_bounded_target_set"] == \
        row["resident_indirect_jump_sites_in_ledger"]
    assert row["query_call_sites_with_a_gate_bounded_target_set"] == 0
    assert row["out_of_gate_scope_sites"], (
        "the gate is resident-only; overlay sites must be named, not dropped")


def test_a_site_missing_from_the_gate_fails_closed(repo_tmp):
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    gate["indirect_control"]["jr_sites"] = gate["indirect_control"]["jr_sites"][:-40]
    doctored = repo_tmp / "gate.json"
    payload = json.dumps(gate, indent=1, sort_keys=True) + "\n"
    doctored.write_text(payload, encoding="utf-8")

    def mutate(seed):
        seed["evidence_receipts"]["static_asm_gate"] = {
            "path": str(doctored.relative_to(ROOT)),
            "sha256": hashlib.sha256(payload.encode()).hexdigest()}
    proc = _seed_variant(repo_tmp, mutate)
    assert proc.returncode != 0
    assert "absent from the gate's typed candidate universe" in (
        proc.stderr + proc.stdout)


def test_growing_the_closure_did_not_move_the_window_access_census(retained):
    """The residual argument rests on this: accesses are found without reachability.

    Seeding the callback targets grew the closure by ~100 functions and the
    window-access count did not move, because every hit is already seeded from a
    whole-universe scan.
    """
    query, summary = retained
    assert summary["accesses_into_windows"] == 124
    assert summary["whole_universe_accesses_not_emitted"] == 0
    assert summary["callback_target_functions_seeded"] > 0
    kinds = [access["kind"] for access in query["accesses"]]
    assert kinds.count("write") == 58 and kinds.count("read") == 66

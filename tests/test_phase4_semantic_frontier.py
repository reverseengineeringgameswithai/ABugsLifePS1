"""Contract, solver, mutation, and authority guards for semantic frontiers."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_semantic_frontier as frontier  # noqa: E402


def index(minimum=0, maximum=4, *, modulus=None, remainder=None,
          signedness="unsigned"):
    return {
        "minimum": minimum, "maximum_exclusive": maximum,
        "congruence_modulus": modulus, "congruence_remainder": remainder,
        "signedness": signedness, "evidence": "synthetic bounded index evidence",
    }


LEDGER = ROOT / "analysis/phase4_f01_frontier_blockers.json" if False else None


def _mechanical_completeness(complete: bool = True):
    """A synthetic query still has to satisfy the /2 mechanical gate.

    The gate is deliberately unsatisfiable without a real ledger and a real
    attesting tool, so the fixture points at the repository's own extractor and
    its retained ledger rather than inventing one.
    """
    import hashlib
    relative = ("tests/fixtures/frontier_empty_ledger.json" if complete
                else "analysis/phase4_f01_frontier_blockers.json")
    ledger = ROOT / relative
    tool = ROOT / "tools/phase4_frontier_extractor.py"
    raw = ledger.read_bytes()
    rows = sum(len(v) for v in json.loads(raw).values() if isinstance(v, list))
    return {
        "complete": complete,
        "evidence": "synthetic query bound to a retained blocker ledger",
        "ledger_path": relative,
        "ledger_sha256": hashlib.sha256(raw).hexdigest(),
        "unemitted_resolved_accesses": 0,
        "retained_blockers": rows,
        "attested_by": {
            "tool": "tools/phase4_frontier_extractor.py",
            "tool_sha256": hashlib.sha256(tool.read_bytes()).hexdigest(),
            "seed_path": "config/phase4_f01_frontier_seed.yaml",
            "seed_sha256": hashlib.sha256(
                (ROOT / "config/phase4_f01_frontier_seed.yaml").read_bytes()).hexdigest(),
            "source_index_path": "analysis/phase4_static_frontier_index.json",
            "source_index_sha256": hashlib.sha256(
                (ROOT / "analysis/phase4_static_frontier_index.json").read_bytes()).hexdigest(),
            "query_path": "config/phase4_f01_frontier_query.yaml",
            "summary_path": "analysis/phase4_f01_frontier_extraction.json",
            "query_digest": "0" * 64,   # replaced by _bind() once the body exists
        },
    }


# There is deliberately NO provenance stub here. compile_frontier verifies
# provenance itself and takes no such parameter, so a synthetic document -- which
# has no extractor behind it -- can never be ready. Every expectation below
# therefore carries PROVENANCE_UNVERIFIED, which is the correct verdict for a
# hand-built query and is exactly what stops one being promoted.


def _bind(document):
    """Attach a query_digest that actually covers this synthetic document."""
    import hashlib
    stripped = {k: v for k, v in document.items() if k != "mechanical_completeness"}
    stripped["mechanical_completeness"] = {
        k: v for k, v in document["mechanical_completeness"].items() if k != "attested_by"}
    canonical = (json.dumps(stripped, indent=1, sort_keys=True) + "\n").encode()
    document["mechanical_completeness"]["attested_by"]["query_digest"] = \
        hashlib.sha256(canonical).hexdigest()
    return document


def query():
    return _bind({
        "schema": frontier.SCHEMA,
        "mechanical_completeness": _mechanical_completeness(),
        "target": {
            "id": "synthetic-frontier", "row_id": "TEST_row",
            "scope_id": "state-window", "scope_statement": "Synthetic state window only",
        },
        "universe": {
            "images": [{
                "id": "resident", "sha256": "1" * 64,
                "base": 0x80010000, "end": 0x80020000, "census_complete": True,
            }],
            "categories": [
                {"id": value, "disposition": "required",
                 "evidence": "Synthetic category is relevant to this proof."}
                for value in frontier.REQUIRED_CATEGORIES
            ],
        },
        "windows": [{"id": "state", "start": 0x80018000, "end": 0x80018010}],
        "functions": [
            {
                "id": "root", "image": "resident", "start": 0x80010000,
                "end": 0x80010040,
                "direct_calls": [{"site": 0x80010010, "target": "worker"}],
                "indirect_calls": [{"site": 0x80010020, "table": "dispatch"}],
                "consumer_categories": ["callers", "callees", "downstream_consumers"],
            },
            {
                "id": "worker", "image": "resident", "start": 0x80010100,
                "end": 0x80010140, "direct_calls": [], "indirect_calls": [],
                "consumer_categories": ["callees"],
            },
        ],
        "roots": ["root"],
        "callbacks": [{
            "id": "update", "targets": ["worker"], "complete": True,
            "evidence": "synthetic callback table",
        }],
        "indirect_tables": [{
            "id": "dispatch", "targets": ["worker"], "complete": True,
            "evidence": "synthetic finite target set",
        }],
        "boundary_owners": [],
        "accesses": [
            {
                "id": "reader", "image": "resident", "pc": 0x80010104,
                "kind": "read", "width": 2,
                "expression": {"base": 0x80018000, "offset": 0, "scale": 2,
                               "index": index(), "arithmetic": "no_wrap"},
                "evidence": "synthetic reader",
            },
            {
                "id": "writer", "image": "resident", "pc": 0x80010108,
                "kind": "write", "width": 4,
                "expression": {"base": 0x80017000, "offset": 0, "scale": 4,
                               "index": index(), "arithmetic": "no_wrap"},
                "evidence": "synthetic disjoint writer",
            },
        ],
        "residuals": [],
        "authority": copy.deepcopy(frontier.AUTHORITY),
    })


def test_closed_query_enumerates_all_item2_categories_and_emits_counterexample():
    report = frontier.compile_frontier(query())
    assert report["schema"] == frontier.OUTPUT_SCHEMA
    # A synthetic document has no extractor behind it, so a real regeneration is
    # impossible and PROVENANCE_UNVERIFIED is the CORRECT sole blocker. Everything
    # this test exists to check -- categories, graph, solver -- is unaffected.
    assert report["verdicts"] == {
        "strict_frontier_closed": False,
        "item2_ready_for_review": False,
        "dimension_promoted": False,
        "review_blockers": ["PROVENANCE_UNVERIFIED"],
    }
    assert report["universe"]["missing_categories"] == []
    assert set(report["graph"]["reached_functions"]) == {"root", "worker"}
    reader = next(row for row in report["accesses"]["results"]
                  if row["id"] == "reader")
    assert reader["classification"] == "intersects"
    assert reader["intersections"] == ["state"]
    assert reader["witness"]["index"] in range(4)
    assert 0x80018000 <= reader["witness"]["effective_address"] < 0x80018010
    writer = next(row for row in report["accesses"]["results"]
                  if row["id"] == "writer")
    assert writer["classification"] == "disjoint" and writer["witness"] is None


def test_unknown_can_be_review_bounded_without_becoming_strict_compiler_closure():
    document = query()
    document["accesses"][1]["expression"]["index"] = None
    document["residuals"] = [{
        "id": "unknown-writer-boundary",
        "boundary": "The unresolved writer base belongs to a separately owned pool.",
        "evidence": "The pool owner and non-overlap extent are independently recorded.",
        "next_experiment": "Re-run the pool extent generator and reject any overlap.",
        "intersects_dimension": False, "disposition": "bounded_disjoint",
        "proof_basis": "documented_extent", "covered_ids": ["writer"],
    }]
    _bind(document)
    report = frontier.compile_frontier(document)
    assert report["verdicts"]["strict_frontier_closed"] is False
    assert report["verdicts"]["review_blockers"] == ["PROVENANCE_UNVERIFIED"], \
        "a synthetic document must be blocked only by its (impossible) provenance"
    assert report["residuals"]["covered_unknowns"] == ["writer"]


def test_unknown_without_residual_fails_item2_instead_of_becoming_disjoint():
    document = query()
    document["accesses"][1]["expression"]["index"] = None
    _bind(document)
    report = frontier.compile_frontier(document)
    assert report["accesses"]["unknown_ids"] == ["writer"]
    assert report["residuals"]["uncovered_unknowns"] == ["writer"]
    assert report["verdicts"]["item2_ready_for_review"] is False
    assert "UNBOUNDED_UNKNOWN" in report["verdicts"]["review_blockers"]


def test_incomplete_callback_is_an_enumerated_unknown_and_can_be_residualized():
    document = query()
    document["callbacks"][0]["complete"] = False
    _bind(document)
    report = frontier.compile_frontier(document)
    assert report["graph"]["unresolved_edges"] == [{
        "id": "callback:update", "kind": "callback",
        "reason": "callback target set is explicitly incomplete",
    }]
    assert report["verdicts"]["item2_ready_for_review"] is False
    document["residuals"] = [{
        "id": "callback-owner", "boundary": "Callback registration is owned externally.",
        "evidence": "The external owner retains the exhaustive callback census.",
        "next_experiment": "Import and hash-check that callback target census.",
        "intersects_dimension": False, "disposition": "owned_boundary",
        "proof_basis": "external_owner", "covered_ids": ["callback:update"],
    }]
    _bind(document)
    report = frontier.compile_frontier(document)
    assert report["verdicts"]["review_blockers"] == ["PROVENANCE_UNVERIFIED"], \
        "a synthetic document must be blocked only by its (impossible) provenance"
    assert report["verdicts"]["strict_frontier_closed"] is False


def test_irrelevant_category_requires_explicit_evidence_backed_not_applicable():
    document = query()
    document["callbacks"] = []
    callback = next(row for row in document["universe"]["categories"]
                    if row["id"] == "callbacks")
    callback.update(disposition="not_applicable",
                    evidence="The declared subsystem ABI has no callback registration surface.")
    _bind(document)
    report = frontier.compile_frontier(document)
    assert report["verdicts"]["review_blockers"] == ["PROVENANCE_UNVERIFIED"], \
        "a synthetic document must be blocked only by its (impossible) provenance"
    assert report["universe"]["categories"]["callbacks"] == {
        "disposition": "not_applicable", "enumerated_records": 0}
    callback["evidence"] = ""
    with pytest.raises(frontier.FrontierError, match="non-empty"):
        _bind(document)
        frontier.validate_query(document)


def test_signed_congruence_and_u32_wrap_are_solver_bounded():
    document = query()
    expression = document["accesses"][0]["expression"]
    expression.update(base=0x10, offset=0, scale=4, arithmetic="u32_wrap")
    expression["index"] = index(-8, 0, modulus=2, remainder=0, signedness="signed")
    document["windows"] = [{"id": "wrapped", "start": 0xFFFFFFF0,
                            "end": 0xFFFFFFF8}]
    _bind(document)
    report = frontier.compile_frontier(document)
    reader = next(row for row in report["accesses"]["results"]
                  if row["id"] == "reader")
    assert reader["classification"] == "intersects"
    assert reader["witness"]["index"] in {-8, -6, -4, -2}
    assert reader["witness"]["effective_address"] >= 0xFFFFFFF0


def test_solver_unknown_remains_unknown_instead_of_becoming_a_disjoint_proof(monkeypatch):
    real = frontier._import_z3()

    class UnknownSolver:
        def __init__(self):
            self.inner = real.Solver()

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def check(self):
            return real.unknown

        def reason_unknown(self):
            return "synthetic timeout"

    class Z3Proxy:
        sat = real.sat
        unsat = real.unsat
        unknown = real.unknown

        def Solver(self):
            return UnknownSolver()

        def __getattr__(self, name):
            return getattr(real, name)

    proxy = Z3Proxy()
    monkeypatch.setattr(frontier, "_import_z3", lambda: proxy)
    result = frontier.classify_access(query()["accesses"][0], query()["windows"])
    assert result == {
        "id": "reader", "classification": "unknown",
        "reason": "Z3 did not decide the bounded query: synthetic timeout",
        "intersections": [], "witness": None,
    }


@pytest.mark.parametrize("mutate,match", [
    (lambda row: row.update(schema="abl-phase4-semantic-frontier-query/99"),
     "must use"),
    (lambda row: row["authority"].update(promotes_dimension=True), "authority"),
    (lambda row: row["universe"]["images"][0].update(base=True), "integer"),
    (lambda row: row["accesses"][0].update(width=True), "integer"),
    (lambda row: row["accesses"][0]["expression"].update(scale=0), "non-zero"),
    (lambda row: row["accesses"][0]["expression"]["index"].update(
        maximum_exclusive=True), "bounds"),
    (lambda row: row["residuals"].append({
        "id": "bad", "boundary": "x", "evidence": "y", "next_experiment": "z",
        "intersects_dimension": True, "disposition": "bounded_disjoint",
        "proof_basis": "documented_extent", "covered_ids": ["writer"]}),
     "intersects Item 2"),
])
def test_schema_and_bool_integer_mutations_fail_closed(mutate, match):
    document = query()
    mutate(document)
    with pytest.raises(frontier.FrontierError, match=match):
        _bind(document)
        frontier.validate_query(document)


def test_residual_double_coverage_and_nonunknown_coverage_are_reported():
    document = query()
    document["accesses"][1]["expression"]["index"] = None
    template = {
        "boundary": "Unknown writer is bounded by an independently typed object.",
        "evidence": "The object's exact allocation extent excludes the target window.",
        "next_experiment": "Regenerate the allocation and access census.",
        "intersects_dimension": False, "disposition": "bounded_disjoint",
        "proof_basis": "typed_record", "covered_ids": ["writer"],
    }
    document["residuals"] = [dict(template, id="a"), dict(template, id="b")]
    _bind(document)
    report = frontier.compile_frontier(document)
    assert any("covered by both" in value for value in report["residuals"]["errors"])
    document["residuals"] = [dict(template, id="reader-bound", covered_ids=["reader"])]
    _bind(document)
    report = frontier.compile_frontier(document)
    assert any("non-unknown" in value for value in report["residuals"]["errors"])


def test_call_sites_and_boundary_owners_cannot_drift_outside_the_graph():
    document = query()
    document["functions"][0]["direct_calls"][0]["site"] = 0x80010110
    with pytest.raises(frontier.FrontierError, match="outside its source function"):
        _bind(document)
        frontier.validate_query(document)

    document = query()
    document["boundary_owners"] = [{
        "edge": "ghost@0x80010000->outside", "owner": "another subsystem",
        "reason": "Synthetic owner must not silently survive graph drift.",
        "evidence": "The declaration intentionally matches no traversed edge.",
    }]
    _bind(document)
    report = frontier.compile_frontier(document)
    assert report["graph"]["unused_boundary_owners"] == [
        "ghost@0x80010000->outside"]
    assert report["verdicts"]["item2_ready_for_review"] is False
    assert "UNUSED_BOUNDARY_OWNER" in report["verdicts"]["review_blockers"]


def test_cli_output_is_deterministic_and_check_detects_staleness(tmp_path):
    source = tmp_path / "query.yaml"
    source.write_text(json.dumps(query()), encoding="utf-8")
    output = ROOT / "analysis" / "phase4_semantic_frontier_test.tmp.json"
    try:
        first = subprocess.run(
            [sys.executable, str(ROOT / "tools/phase4_semantic_frontier.py"),
             str(source), "--output", str(output)], cwd=ROOT,
            text=True, capture_output=True, check=False)
        assert first.returncode == 0, first.stderr
        original = output.read_bytes()
        second = subprocess.run(
            [sys.executable, str(ROOT / "tools/phase4_semantic_frontier.py"),
             str(source), "--output", str(output), "--check"], cwd=ROOT,
            text=True, capture_output=True, check=False)
        assert second.returncode == 0, second.stderr
        output.write_text("{}\n", encoding="utf-8")
        stale = subprocess.run(
            [sys.executable, str(ROOT / "tools/phase4_semantic_frontier.py"),
             str(source), "--output", str(output), "--check"], cwd=ROOT,
            text=True, capture_output=True, check=False)
        assert stale.returncode != 0 and "stale" in stale.stderr
        assert original != output.read_bytes()
    finally:
        output.unlink(missing_ok=True)

#!/usr/bin/env python3
"""Compile a scoped, falsifiable semantic frontier for a Phase-4 subsystem.

The compiler deliberately exposes two different conclusions:

* ``strict_frontier_closed`` means the declared compiler universe has no unknown
  call edge or memory intersection.
* ``item2_ready_for_review`` means every required Item-2 category is enumerated
  and every remaining boundary is represented by a well-formed, explicitly
  non-intersecting residual.

Neither conclusion changes the campaign registry or promotes a dimension.  The
result is a review packet, not a self-certified proof.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "abl-phase4-semantic-frontier-query/2"
LEDGER_SCHEMA = "abl-phase4-frontier-blockers/1"
# The TRUST ROOT is owned by this checker, never by the document under review.
# Hashing a document-chosen file only proves which file ran -- a hash-correct
# no-op that exits zero would otherwise "reproduce" anything.
TRUSTED_EXTRACTORS = ("tools/phase4_frontier_extractor.py",)
# Only a real regeneration may support a ready verdict. Any caller can hand in
# {"verified": True}; only this method name means the artifacts were rebuilt.
PROVENANCE_METHOD = "regeneration"
LEDGER_CATEGORIES = ("omitted_direct_edges", "unresolvable_direct_edges",
                     "omitted_incoming_callers", "unresolved_accesses",
                     "direct_jumps_out", "indirect_jumps", "incoming_jumps",
                     "unanalysed_extents", "binary_scan_unscanned_images")
OUTPUT_SCHEMA = "abl-phase4-semantic-frontier-result/2"
REQUIRED_CATEGORIES = (
    "callers", "callees", "callbacks", "indirect_tables", "overlays",
    "readers", "writers", "downstream_consumers",
)
ACCESS_KINDS = {"read", "write", "read_write", "address_take"}
ARITHMETIC = {"no_wrap", "u32_wrap"}
RESIDUAL_DISPOSITIONS = {"bounded_disjoint", "owned_boundary"}
PROOF_BASES = {
    "exact_address", "bounded_index", "documented_extent", "adjacent_object",
    "materialization_census", "typed_record", "declared_indirect_target_set",
    "external_owner", "runtime_falsifier", "reviewed_manual",
}
AUTHORITY = {
    "changes_campaign_registry": False,
    "promotes_dimension": False,
    "runtime_silence_proves_absence": False,
    "frame_capsule_proves_exact_causality": False,
    "unknown_is_disjoint": False,
    "fresh_verifier_required": True,
}


class FrontierError(RuntimeError):
    """A query or its proof contract is malformed."""


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _exact_keys(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        actual = sorted(value) if type(value) is dict else type(value).__name__
        raise FrontierError(f"{field} fields differ: {actual!r}")
    return value


def _string(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise FrontierError(f"{field} must be a non-empty string")
    return value


def _integer(value: Any, field: str, *, minimum: int = 0,
             maximum: int = 0x1_0000_0000) -> int:
    if type(value) is not int or not minimum <= value < maximum:
        raise FrontierError(f"{field} must be an integer in [{minimum}, {maximum})")
    return value


def _hex64(value: Any, field: str) -> str:
    if type(value) is not str or len(value) != 64 or any(
            char not in "0123456789abcdef" for char in value):
        raise FrontierError(f"{field} must be a lowercase SHA-256")
    return value


def _unique(rows: list[dict[str, Any]], key: str, field: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        identity = _string(row.get(key), f"{field}[{index}].{key}")
        if identity in result:
            raise FrontierError(f"{field} duplicates {identity!r}")
        result[identity] = row
    return result


def load_query(path: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise FrontierError(f"cannot load frontier query: {exc}") from exc
    validate_query(document)
    return document


def validate_query(document: Any) -> dict[str, Any]:
    top = _exact_keys(document, {
        "schema", "target", "universe", "windows", "functions", "roots",
        "callbacks", "indirect_tables", "boundary_owners", "accesses",
        "residuals", "authority", "mechanical_completeness",
    }, "query")
    if top["schema"] != SCHEMA:
        raise FrontierError(f"query must use {SCHEMA}")
    _exact_keys(top["target"], {"id", "row_id", "scope_id", "scope_statement"},
                "target")
    for key, value in top["target"].items():
        _string(value, f"target.{key}")
    universe = _exact_keys(top["universe"], {"images", "categories"}, "universe")
    if type(universe["images"]) is not list or not universe["images"]:
        raise FrontierError("universe.images must be a non-empty list")
    images = _unique(universe["images"], "id", "universe.images")
    for image_id, image in images.items():
        _exact_keys(image, {"id", "sha256", "base", "end", "census_complete"},
                    f"image.{image_id}")
        _hex64(image["sha256"], f"image.{image_id}.sha256")
        base = _integer(image["base"], f"image.{image_id}.base")
        end = _integer(image["end"], f"image.{image_id}.end")
        if end <= base:
            raise FrontierError(f"image.{image_id} has an empty extent")
        if type(image["census_complete"]) is not bool:
            raise FrontierError(f"image.{image_id}.census_complete must be Boolean")
    if type(universe["categories"]) is not list:
        raise FrontierError("universe.categories must be a list")
    category_rows = _unique(universe["categories"], "id", "universe.categories")
    if set(category_rows) != set(REQUIRED_CATEGORIES):
        raise FrontierError("every Item-2 category must have exactly one disposition")
    for category_id, category in category_rows.items():
        _exact_keys(category, {"id", "disposition", "evidence"},
                    f"category.{category_id}")
        if category["disposition"] not in {"required", "not_applicable"}:
            raise FrontierError(f"category.{category_id}.disposition is invalid")
        _string(category["evidence"], f"category.{category_id}.evidence")

    if type(top["windows"]) is not list or not top["windows"]:
        raise FrontierError("windows must be a non-empty list")
    windows = _unique(top["windows"], "id", "windows")
    for window_id, window in windows.items():
        _exact_keys(window, {"id", "start", "end"}, f"window.{window_id}")
        start = _integer(window["start"], f"window.{window_id}.start")
        end = _integer(window["end"], f"window.{window_id}.end")
        if end <= start:
            raise FrontierError(f"window.{window_id} has an empty extent")

    if type(top["functions"]) is not list:
        raise FrontierError("functions must be a list")
    functions = _unique(top["functions"], "id", "functions")
    for function_id, function in functions.items():
        _exact_keys(function, {
            "id", "image", "start", "end", "direct_calls", "indirect_calls",
            "consumer_categories",
        }, f"function.{function_id}")
        if function["image"] not in images:
            raise FrontierError(f"function.{function_id} names an unknown image")
        start = _integer(function["start"], f"function.{function_id}.start")
        end = _integer(function["end"], f"function.{function_id}.end")
        image = images[function["image"]]
        if end <= start or start < image["base"] or end > image["end"]:
            raise FrontierError(f"function.{function_id} is outside its image")
        for edge_index, edge in enumerate(function["direct_calls"]):
            _exact_keys(edge, {"site", "target"},
                        f"function.{function_id}.direct_calls[{edge_index}]")
            site = _integer(
                edge["site"], f"function.{function_id}.direct_calls[{edge_index}].site")
            if not start <= site < end:
                raise FrontierError(
                    f"function.{function_id}.direct_calls[{edge_index}].site "
                    "lies outside its source function")
            _string(edge["target"], f"function.{function_id}.direct_calls[{edge_index}].target")
        for edge_index, edge in enumerate(function["indirect_calls"]):
            _exact_keys(edge, {"site", "table"},
                        f"function.{function_id}.indirect_calls[{edge_index}]")
            site = _integer(
                edge["site"], f"function.{function_id}.indirect_calls[{edge_index}].site")
            if not start <= site < end:
                raise FrontierError(
                    f"function.{function_id}.indirect_calls[{edge_index}].site "
                    "lies outside its source function")
            _string(edge["table"], f"function.{function_id}.indirect_calls[{edge_index}].table")
        categories = function["consumer_categories"]
        if type(categories) is not list or not categories or any(
                value not in REQUIRED_CATEGORIES for value in categories):
            raise FrontierError(f"function.{function_id}.consumer_categories is invalid")

    if type(top["roots"]) is not list or not top["roots"]:
        raise FrontierError("roots must be a non-empty list")
    if len(set(top["roots"])) != len(top["roots"]):
        raise FrontierError("roots contains duplicates")
    for root in top["roots"]:
        if root not in functions:
            raise FrontierError(f"unknown frontier root {root!r}")

    if type(top["callbacks"]) is not list:
        raise FrontierError("callbacks must be a list")
    callbacks = _unique(top["callbacks"], "id", "callbacks")
    if type(top["indirect_tables"]) is not list:
        raise FrontierError("indirect_tables must be a list")
    tables = _unique(top["indirect_tables"], "id", "indirect_tables")
    for group_name, groups in (("callback", callbacks), ("indirect_table", tables)):
        for group_id, group in groups.items():
            _exact_keys(group, {"id", "targets", "complete", "evidence"},
                        f"{group_name}.{group_id}")
            if type(group["targets"]) is not list or len(set(group["targets"])) != len(
                    group["targets"]):
                raise FrontierError(f"{group_name}.{group_id}.targets is invalid")
            for target in group["targets"]:
                if target not in functions:
                    raise FrontierError(f"{group_name}.{group_id} has unknown target {target!r}")
            if type(group["complete"]) is not bool:
                raise FrontierError(f"{group_name}.{group_id}.complete must be Boolean")
            _string(group["evidence"], f"{group_name}.{group_id}.evidence")
    for function in functions.values():
        for edge in function["indirect_calls"]:
            if edge["table"] not in tables:
                raise FrontierError(
                    f"function.{function['id']} names unknown table {edge['table']!r}")

    if type(top["boundary_owners"]) is not list:
        raise FrontierError("boundary_owners must be a list")
    owners = _unique(top["boundary_owners"], "edge", "boundary_owners")
    for edge, owner in owners.items():
        _exact_keys(owner, {"edge", "owner", "reason", "evidence"},
                    f"boundary_owner.{edge}")
        for key in ("owner", "reason", "evidence"):
            _string(owner[key], f"boundary_owner.{edge}.{key}")

    if type(top["accesses"]) is not list:
        raise FrontierError("accesses must be a list")
    accesses = _unique(top["accesses"], "id", "accesses")
    for access_id, access in accesses.items():
        _exact_keys(access, {"id", "image", "pc", "kind", "width", "expression",
                             "evidence"}, f"access.{access_id}")
        if access["image"] not in images:
            raise FrontierError(f"access.{access_id} names unknown image")
        pc = _integer(access["pc"], f"access.{access_id}.pc")
        image = images[access["image"]]
        if not image["base"] <= pc < image["end"]:
            raise FrontierError(f"access.{access_id}.pc lies outside its image")
        if access["kind"] not in ACCESS_KINDS:
            raise FrontierError(f"access.{access_id}.kind is invalid")
        _integer(access["width"], f"access.{access_id}.width", minimum=1, maximum=17)
        expression = _exact_keys(access["expression"], {
            "base", "offset", "scale", "index", "arithmetic",
        }, f"access.{access_id}.expression")
        _integer(expression["base"], f"access.{access_id}.expression.base")
        if type(expression["offset"]) is not int:
            raise FrontierError(f"access.{access_id}.expression.offset must be an integer")
        if type(expression["scale"]) is not int or expression["scale"] == 0:
            raise FrontierError(f"access.{access_id}.expression.scale must be non-zero")
        if expression["arithmetic"] not in ARITHMETIC:
            raise FrontierError(f"access.{access_id}.expression.arithmetic is invalid")
        index = expression["index"]
        if index is not None:
            _exact_keys(index, {
                "minimum", "maximum_exclusive", "congruence_modulus",
                "congruence_remainder", "signedness", "evidence",
            }, f"access.{access_id}.expression.index")
            if type(index["minimum"]) is not int or type(index["maximum_exclusive"]) is not int:
                raise FrontierError(f"access.{access_id}.index bounds must be integers")
            if index["maximum_exclusive"] <= index["minimum"]:
                raise FrontierError(f"access.{access_id}.index has an empty range")
            modulus = index["congruence_modulus"]
            remainder = index["congruence_remainder"]
            if (modulus is None) != (remainder is None):
                raise FrontierError(f"access.{access_id}.index congruence is incomplete")
            if modulus is not None and (type(modulus) is not int or modulus < 1 or
                                        type(remainder) is not int or not 0 <= remainder < modulus):
                raise FrontierError(f"access.{access_id}.index congruence is invalid")
            if index["signedness"] not in {"signed", "unsigned"}:
                raise FrontierError(f"access.{access_id}.index signedness is invalid")
            _string(index["evidence"], f"access.{access_id}.index.evidence")
        _string(access["evidence"], f"access.{access_id}.evidence")

    if type(top["residuals"]) is not list:
        raise FrontierError("residuals must be a list")
    residuals = _unique(top["residuals"], "id", "residuals")
    for residual_id, residual in residuals.items():
        _exact_keys(residual, {
            "id", "boundary", "evidence", "next_experiment",
            "intersects_dimension", "disposition", "proof_basis", "covered_ids",
        }, f"residual.{residual_id}")
        for key in ("boundary", "evidence", "next_experiment"):
            _string(residual[key], f"residual.{residual_id}.{key}")
        if residual["intersects_dimension"] is not False:
            raise FrontierError(f"residual.{residual_id} intersects Item 2")
        if residual["disposition"] not in RESIDUAL_DISPOSITIONS:
            raise FrontierError(f"residual.{residual_id}.disposition is invalid")
        if residual["proof_basis"] not in PROOF_BASES:
            raise FrontierError(f"residual.{residual_id}.proof_basis is invalid")
        if type(residual["covered_ids"]) is not list or not residual["covered_ids"] or any(
                type(value) is not str or not value for value in residual["covered_ids"]):
            raise FrontierError(f"residual.{residual_id}.covered_ids is invalid")
    # Mechanical completeness is a HARD input, not advisory prose. An extractor
    # that could not project part of the universe into this query must say so
    # here, so a later seed edit cannot quietly buy a ready verdict while known
    # accesses stay invisible to the solver.
    mechanical = _exact_keys(top["mechanical_completeness"], {
        "complete", "evidence", "ledger_sha256", "ledger_path",
        "unemitted_resolved_accesses", "retained_blockers", "attested_by",
    }, "mechanical_completeness")
    # The attestation is bound to THIS query: query_digest covers every part of
    # the document except the attestation itself, so an attestation cannot be
    # lifted onto a hand-built query.
    _ = mechanical
    if type(mechanical["complete"]) is not bool:
        raise FrontierError("mechanical_completeness.complete must be Boolean")
    _string(mechanical["evidence"], "mechanical_completeness.evidence")
    if mechanical["ledger_sha256"] is not None:
        _hex64(mechanical["ledger_sha256"], "mechanical_completeness.ledger_sha256")
    if type(mechanical["unemitted_resolved_accesses"]) is not int or \
            mechanical["unemitted_resolved_accesses"] < 0:
        raise FrontierError(
            "mechanical_completeness.unemitted_resolved_accesses must be a count")
    if type(mechanical["retained_blockers"]) is not int or mechanical["retained_blockers"] < 0:
        raise FrontierError("mechanical_completeness.retained_blockers must be a count")
    if mechanical["complete"] and mechanical["unemitted_resolved_accesses"]:
        raise FrontierError(
            "mechanical_completeness.complete is true while resolved accesses were not emitted")
    if mechanical["complete"] and mechanical["retained_blockers"]:
        raise FrontierError(
            "mechanical_completeness.complete is true while "
            f"{mechanical['retained_blockers']} mechanical blockers stand")
    # The counts above are only as trustworthy as the ledger they summarise, so
    # verify the ledger itself: a hand-edited count cannot survive this.
    # An attestation is required even when zero blockers remain: `complete` must
    # be an extractor-attested FACT, never an assertion a hand edit can make.
    attested = _exact_keys(mechanical["attested_by"], {
        "tool", "tool_sha256", "seed_path", "seed_sha256",
        "source_index_path", "source_index_sha256", "query_path", "summary_path",
        "query_digest",
    }, "mechanical_completeness.attested_by")
    _string(attested["tool"], "mechanical_completeness.attested_by.tool")
    for key in ("tool_sha256", "seed_sha256", "source_index_sha256"):
        _hex64(attested[key], f"mechanical_completeness.attested_by.{key}")
    _string(attested["tool"], "mechanical_completeness.attested_by.tool")
    # The attestation must name a tool that exists here and hashes as claimed,
    # so `complete` cannot be asserted by editing the block.
    if attested["tool"] not in TRUSTED_EXTRACTORS:
        raise FrontierError(
            f"attested_by.tool {attested['tool']!r} is not a checker-trusted extractor; "
            f"the trust root is owned here, not by the query: {list(TRUSTED_EXTRACTORS)}")
    tool_path = ROOT / attested["tool"]
    if not tool_path.is_file():
        raise FrontierError(f"attesting tool not found: {attested['tool']}")
    if sha256_bytes(tool_path.read_bytes()) != attested["tool_sha256"]:
        raise FrontierError("attested_by.tool_sha256 does not match the tool on disk")
    # The seed and source index must exist here and hash as attested.
    for name in ("query_path", "summary_path"):
        relative = Path(_string(attested[name], f"attested_by.{name}"))
        if ".." in relative.parts or relative.is_absolute():
            raise FrontierError(f"attested_by.{name} must be repo-relative")
    for name, hash_key in (("seed_path", "seed_sha256"),
                           ("source_index_path", "source_index_sha256")):
        relative = Path(_string(attested[name], f"attested_by.{name}"))
        if ".." in relative.parts or relative.is_absolute():
            raise FrontierError(f"attested_by.{name} must be repo-relative")
        source = ROOT / relative
        if not source.is_file():
            raise FrontierError(f"attested source missing: {attested[name]}")
        if sha256_bytes(source.read_bytes()) != attested[hash_key]:
            raise FrontierError(f"attested_by.{hash_key} does not match {attested[name]}")
    _hex64(attested["query_digest"], "attested_by.query_digest")
    stripped = {key: value for key, value in top.items() if key != "mechanical_completeness"}
    stripped["mechanical_completeness"] = {
        key: value for key, value in mechanical.items() if key != "attested_by"}
    if sha256_bytes(canonical_json(stripped)) != attested["query_digest"]:
        raise FrontierError(
            "attested_by.query_digest does not cover this query -- an attestation "
            "cannot be reused on a document its tool did not produce")
    if mechanical["ledger_path"] is None:
        raise FrontierError(
            "mechanical_completeness must name a ledger even when no blockers remain; "
            "a null ledger makes `complete` self-certifying")
    if mechanical["ledger_path"] is not None:
        _string(mechanical["ledger_path"], "mechanical_completeness.ledger_path")
        relative = Path(mechanical["ledger_path"])
        if ".." in relative.parts or relative.is_absolute():
            raise FrontierError("mechanical_completeness.ledger_path must be repo-relative")
        ledger = ROOT / relative
        if not ledger.is_file():
            raise FrontierError(f"mechanical_completeness ledger missing: {ledger}")
        raw = ledger.read_bytes()
        if sha256_bytes(raw) != mechanical["ledger_sha256"]:
            raise FrontierError("mechanical_completeness ledger does not match its sha256")
        ledger_doc = json.loads(raw)
        if ledger_doc.get("schema") != LEDGER_SCHEMA:
            raise FrontierError(f"blocker ledger must use {LEDGER_SCHEMA}")
        present = {key for key, value in ledger_doc.items() if isinstance(value, list)}
        if present != set(LEDGER_CATEGORIES):
            raise FrontierError(
                f"blocker ledger categories {sorted(present)} != {sorted(LEDGER_CATEGORIES)}")
        rows = [row for value in ledger_doc.values() if isinstance(value, list)
                for row in value]
        identities = [row.get("id") for row in rows]
        if any(not identity for identity in identities):
            raise FrontierError("every blocker ledger row must carry a stable id")
        if len(set(identities)) != len(identities):
            duplicates = len(identities) - len(set(identities))
            raise FrontierError(f"blocker ledger has {duplicates} duplicate ids")
        if len(rows) != mechanical["retained_blockers"]:
            raise FrontierError(
                f"mechanical_completeness.retained_blockers ({mechanical['retained_blockers']}) "
                f"disagrees with the ledger ({len(rows)} entries)")
    if top["authority"] != AUTHORITY:
        raise FrontierError("query.authority differs from the non-promotion contract")
    return top


def verify_provenance(document: dict[str, Any]) -> dict[str, Any]:
    """Prove the extractor produced this query, by REGENERATION.

    `query_digest` proves integrity against accidental edits, but it is a public
    hash anyone can recompute, so it cannot prove provenance. The only thing that
    can is re-running the attested extractor against the attested seed and
    requiring the retained artifacts to reproduce byte-for-byte -- and requiring
    the document under review to BE the retained query file.
    """
    import subprocess
    attested = document["mechanical_completeness"]["attested_by"]
    if attested["tool"] not in TRUSTED_EXTRACTORS:
        return {"verified": False, "method": PROVENANCE_METHOD,
                "detail": f"untrusted attesting tool {attested['tool']!r}"}
    tool = ROOT / attested["tool"]          # checker-owned, not document-chosen
    for name in ("query_path", "summary_path", "seed_path"):
        candidate = Path(attested[name])
        if ".." in candidate.parts or candidate.is_absolute():
            return {"verified": False, "method": PROVENANCE_METHOD,
                    "detail": f"attested_by.{name} is not repo-relative"}
        if not (ROOT / candidate).is_file():
            return {"verified": False, "method": PROVENANCE_METHOD,
                    "detail": f"attested {name} does not exist: {attested[name]}"}
    query_path = ROOT / attested["query_path"]
    if not query_path.is_file():
        return {"verified": False, "method": PROVENANCE_METHOD,
                "detail": f"attested query file missing: {attested['query_path']}"}
    try:
        on_disk = yaml.safe_load(query_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return {"verified": False, "method": PROVENANCE_METHOD, "detail": str(exc)}
    if on_disk != document:
        return {"verified": False, "method": PROVENANCE_METHOD,
                "detail": ("the document under review is not the attested query file; "
                           "a hand-built query cannot borrow another query's provenance")}
    proc = subprocess.run(
        [sys.executable, str(tool), str(ROOT / attested["seed_path"]),
         "--output", str(query_path),
         "--summary", str(ROOT / attested["summary_path"]),
         "--blockers", str(ROOT / document["mechanical_completeness"]["ledger_path"]),
         "--check"],
        capture_output=True, text=True, cwd=ROOT)
    if proc.returncode != 0:
        return {"verified": False, "method": PROVENANCE_METHOD,
                "detail": (proc.stderr or proc.stdout).strip()[:300]}
    return {"verified": True, "method": PROVENANCE_METHOD,
            "detail": "extractor --check reproduced query, summary and ledger byte-for-byte"}


def _import_z3() -> Any:
    try:
        import z3
    except ImportError as exc:  # pragma: no cover - environment diagnostic
        raise FrontierError("z3-solver 4.16.0.0 is required") from exc
    version = z3.get_version_string()
    if version != "4.16.0":
        raise FrontierError(f"Z3 version drift: {version} != 4.16.0")
    return z3


def classify_access(access: dict[str, Any], windows: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify one affine effective-address family and return a witness if it intersects."""
    expression = access["expression"]
    index = expression["index"]
    if index is None:
        return {
            "id": access["id"], "classification": "unknown",
            "reason": "index domain is not bounded", "intersections": [],
            "witness": None,
        }
    z3 = _import_z3()
    variable = z3.Int(f"idx_{hashlib.sha256(access['id'].encode()).hexdigest()[:12]}")
    solver = z3.Solver()
    solver.set(timeout=5000)
    solver.add(variable >= index["minimum"], variable < index["maximum_exclusive"])
    if index["congruence_modulus"] is not None:
        solver.add(variable % index["congruence_modulus"] == index["congruence_remainder"])
    mathematical = expression["base"] + expression["offset"] + expression["scale"] * variable
    if expression["arithmetic"] == "no_wrap":
        effective = mathematical
        solver.add(effective >= 0, effective + access["width"] <= 0x1_0000_0000)
    else:
        effective = z3.BV2Int(z3.Int2BV(mathematical, 32), is_signed=False)
        solver.add(effective + access["width"] <= 0x1_0000_0000)
    overlap_terms = []
    for window in windows:
        overlap_terms.append(z3.And(
            effective < window["end"], effective + access["width"] > window["start"]))
    solver.add(z3.Or(overlap_terms))
    outcome = solver.check()
    if outcome == z3.sat:
        model = solver.model()
        chosen_index = model.eval(variable).as_long()
        raw = expression["base"] + expression["offset"] + expression["scale"] * chosen_index
        address = raw if expression["arithmetic"] == "no_wrap" else raw & 0xFFFFFFFF
        intersections = [window["id"] for window in windows
                         if address < window["end"] and
                         address + access["width"] > window["start"]]
        return {
            "id": access["id"], "classification": "intersects",
            "reason": "bounded affine domain has a satisfiable intersection",
            "intersections": intersections,
            "witness": {"index": chosen_index, "effective_address": address},
        }
    if outcome == z3.unknown:
        return {
            "id": access["id"], "classification": "unknown",
            "reason": f"Z3 did not decide the bounded query: {solver.reason_unknown()}",
            "intersections": [], "witness": None,
        }
    if outcome != z3.unsat:  # pragma: no cover - defensive API drift guard
        raise FrontierError(f"unexpected Z3 solver result: {outcome}")
    return {
        "id": access["id"], "classification": "disjoint",
        "reason": "Z3 proved the complete bounded affine domain disjoint",
        "intersections": [], "witness": None,
    }


def _edge_id(source: str, site: int, target: str) -> str:
    return f"{source}@0x{site:08X}->{target}"


def walk_graph(document: dict[str, Any]) -> dict[str, Any]:
    functions = {row["id"]: row for row in document["functions"]}
    tables = {row["id"]: row for row in document["indirect_tables"]}
    owners = {row["edge"]: row for row in document["boundary_owners"]}
    queue = deque(document["roots"])
    reached: set[str] = set()
    edges: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    used_owners: set[str] = set()
    for callback in document["callbacks"]:
        identity = f"callback:{callback['id']}"
        if callback["complete"]:
            edges.append({"id": identity, "kind": "callback",
                          "status": "enumerated", "targets": callback["targets"]})
            queue.extend(callback["targets"])
        else:
            unresolved.append({"id": identity, "kind": "callback",
                               "reason": "callback target set is explicitly incomplete"})
    while queue:
        source_id = queue.popleft()
        if source_id in reached:
            continue
        reached.add(source_id)
        source = functions[source_id]
        for edge in source["direct_calls"]:
            identity = _edge_id(source_id, edge["site"], edge["target"])
            if edge["target"] in functions:
                edges.append({"id": identity, "kind": "direct", "status": "enumerated"})
                queue.append(edge["target"])
            elif identity in owners:
                used_owners.add(identity)
                edges.append({"id": identity, "kind": "direct", "status": "owned_boundary"})
            else:
                unresolved.append({"id": identity, "kind": "direct",
                                   "reason": "target absent and has no boundary owner"})
        for edge in source["indirect_calls"]:
            table = tables[edge["table"]]
            identity = _edge_id(source_id, edge["site"], edge["table"])
            if not table["complete"]:
                unresolved.append({"id": identity, "kind": "indirect",
                                   "reason": "target set is explicitly incomplete"})
            else:
                edges.append({"id": identity, "kind": "indirect",
                              "status": "enumerated", "targets": table["targets"]})
                queue.extend(table["targets"])
    unused_owners = sorted(set(owners) - used_owners)
    return {
        "roots": list(document["roots"]),
        "reached_functions": sorted(reached),
        "enumerated_edges": sorted(edges, key=lambda row: row["id"]),
        "unresolved_edges": sorted(unresolved, key=lambda row: row["id"]),
        "unused_boundary_owners": unused_owners,
    }


def compile_frontier(document: dict[str, Any]) -> dict[str, Any]:
    validate_query(document)
    graph = walk_graph(document)
    access_results = [classify_access(row, document["windows"])
                      for row in document["accesses"]]
    by_access = {row["id"]: row for row in access_results}
    residual_coverage: dict[str, str] = {}
    residual_errors: list[str] = []
    known_boundary_ids = {row["id"] for row in graph["unresolved_edges"]}
    known_boundary_ids |= {row["id"] for row in access_results
                           if row["classification"] == "unknown"}
    for residual in document["residuals"]:
        for covered_id in residual["covered_ids"]:
            if covered_id in residual_coverage:
                residual_errors.append(
                    f"{covered_id} is covered by both {residual_coverage[covered_id]} and "
                    f"{residual['id']}")
            residual_coverage[covered_id] = residual["id"]
            if covered_id not in known_boundary_ids:
                residual_errors.append(
                    f"{residual['id']} covers non-unknown boundary {covered_id}")
    uncovered = sorted(known_boundary_ids - set(residual_coverage))
    category_evidence: dict[str, int] = {key: 0 for key in REQUIRED_CATEGORIES}
    for function in document["functions"]:
        if function["id"] in graph["reached_functions"]:
            for category in function["consumer_categories"]:
                category_evidence[category] += 1
    # Category coverage asks whether the surface was enumerated. Completeness is
    # evaluated separately by strict closure or by residual coverage; counting
    # only already-proven rows here would recreate the Item-2/strict-closure
    # conflation this compiler exists to prevent.
    category_evidence["callbacks"] += len(document["callbacks"])
    category_evidence["indirect_tables"] += len(document["indirect_tables"])
    category_evidence["overlays"] += len(document["universe"]["images"])
    for access in document["accesses"]:
        if access["kind"] in {"read", "read_write"}:
            category_evidence["readers"] += 1
        if access["kind"] in {"write", "read_write"}:
            category_evidence["writers"] += 1
    category_dispositions = {
        row["id"]: row["disposition"] for row in document["universe"]["categories"]}
    missing_categories = [category for category in REQUIRED_CATEGORIES
                          if category_dispositions[category] == "required" and
                          category_evidence[category] == 0]
    image_census_complete = all(row["census_complete"]
                                for row in document["universe"]["images"])
    unknown_accesses = sorted(row["id"] for row in access_results
                              if row["classification"] == "unknown")
    intersecting_accesses = sorted(row["id"] for row in access_results
                                   if row["classification"] == "intersects")
    mechanical = document["mechanical_completeness"]
    # Provenance is NOT a parameter. A caller-supplied dictionary is an assertion,
    # not proof -- `{"verified": True, "method": "regeneration"}` would otherwise
    # buy a ready verdict outright, and checking the method string only makes the
    # assertion more specific. This compiler verifies provenance itself, so no
    # caller can substitute a claim for a regeneration.
    provenance = verify_provenance(document)
    provenance_ok = bool(provenance["verified"]
                         and provenance.get("method") == PROVENANCE_METHOD)
    strict_closed = bool(
        image_census_complete and not graph["unresolved_edges"] and
        not unknown_accesses and not missing_categories and
        not graph["unused_boundary_owners"] and mechanical["complete"] and
        provenance_ok)
    item2_ready = bool(
        image_census_complete and not missing_categories and not uncovered and
        not residual_errors and not graph["unused_boundary_owners"] and
        mechanical["complete"] and provenance_ok)
    review_blockers = []
    if not image_census_complete:
        review_blockers.append("IMAGE_CENSUS_INCOMPLETE")
    if missing_categories:
        review_blockers.append("ITEM2_CATEGORY_MISSING")
    if uncovered:
        review_blockers.append("UNBOUNDED_UNKNOWN")
    if residual_errors:
        review_blockers.append("RESIDUAL_COVERAGE_INVALID")
    if graph["unused_boundary_owners"]:
        review_blockers.append("UNUSED_BOUNDARY_OWNER")
    if not mechanical["complete"]:
        review_blockers.append("MECHANICALLY_INCOMPLETE")
    if not provenance_ok:
        review_blockers.append("PROVENANCE_UNVERIFIED")
    return {
        "schema": OUTPUT_SCHEMA,
        "mechanical_completeness": mechanical,
        "provenance": provenance,
        "target": document["target"],
        "source_query_sha256": sha256_bytes(canonical_json(document)),
        "universe": {
            "images": len(document["universe"]["images"]),
            "image_census_complete": image_census_complete,
            "categories": {
                category: {"disposition": category_dispositions[category],
                           "enumerated_records": category_evidence[category]}
                for category in REQUIRED_CATEGORIES
            },
            "missing_categories": missing_categories,
        },
        "graph": graph,
        "accesses": {
            "results": access_results,
            "counts": {
                "intersects": len(intersecting_accesses),
                "disjoint": sum(row["classification"] == "disjoint"
                                for row in access_results),
                "unknown": len(unknown_accesses),
            },
            "intersecting_ids": intersecting_accesses,
            "unknown_ids": unknown_accesses,
        },
        "residuals": {
            "entries": len(document["residuals"]),
            "covered_unknowns": sorted(residual_coverage),
            "uncovered_unknowns": uncovered,
            "errors": sorted(residual_errors),
        },
        "verdicts": {
            "strict_frontier_closed": strict_closed,
            "item2_ready_for_review": item2_ready,
            "dimension_promoted": False,
            "review_blockers": review_blockers,
        },
        "authority": AUTHORITY,
        "toolchain": {"z3": _import_z3().get_version_string()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true",
                        help="require --output to already equal regenerated bytes")
    args = parser.parse_args()
    document = load_query(args.query)
    result = compile_frontier(document)
    payload = canonical_json(result)
    if args.output is None:
        print(payload.decode(), end="")
        return 0
    output = args.output.resolve(strict=False)
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise FrontierError("tracked frontier output must remain inside the repository") from exc
    if args.check:
        try:
            current = output.read_bytes()
        except OSError as exc:
            raise FrontierError(f"cannot read retained result: {exc}") from exc
        if current != payload:
            raise FrontierError("retained semantic-frontier result is stale")
        print(f"[phase4-semantic-frontier] {args.output}: fresh")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    print(f"[phase4-semantic-frontier] wrote {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FrontierError as exc:
        raise SystemExit(f"[phase4-semantic-frontier] ERROR: {exc}") from exc

#!/usr/bin/env python3
"""Validate and rank inbound PC-to-PS1 semantic lead packets.

This is a hypothesis-selection tool, not an evidence-promotion tool. It reads a
versioned external lead and a curated PS1 candidate catalog, validates their
identities, and ranks exact normalized semantic features. It never launches an
emulator, reads a save state, mutates a binary, or writes unless ``--output`` is
explicitly supplied.

Examples:

  python tools/cross_port_semantic_bridge.py validate-lead LEAD.json \
    --source-repo ~/ABLPC
  python tools/cross_port_semantic_bridge.py validate-catalog CATALOG.json \
    --target-repo .
  python tools/cross_port_semantic_bridge.py rank LEAD.json CATALOG.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any


LEAD_SCHEMA = "abl-cross-port-semantic-lead-v1"
CATALOG_SCHEMA = "abl-cross-port-semantic-candidate-catalog-v1"
NORMAL_FORM = "abl-semantic-feature-set-v1"
RESULT_SCHEMA = "abl-pc-to-ps1-semantic-ranking-v1"

PS1_BINARY_ID = "SCUS_942.88"
PS1_BINARY_SHA256 = "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"
PS1_ARCHITECTURE = "mips-r3000a-le"
PC_ARCHITECTURE = "x86-32-le"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
LEAD_ID_RE = re.compile(r"^PC2PS1-[A-Z0-9][A-Z0-9-]{7,95}$")
CANDIDATE_ID_RE = re.compile(r"^PS1-CAND-[A-Z0-9][A-Z0-9-]{3,95}$")
SEMANTIC_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,95}$")
ATTRIBUTE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
LOCATOR_KINDS = {"function", "instruction_window", "data", "file_offset"}
FEATURE_KINDS = {
    "table_shape",
    "index_expression",
    "operation",
    "guard",
    "threshold",
    "state_transition",
    "control_flow",
    "selector_domain",
    "call_shape",
}
MAX_JSON_BYTES = 4 * 1024 * 1024


class BridgeError(ValueError):
    """A packet, catalog, provenance check, or output boundary failed."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BridgeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_strict(path: Path) -> tuple[dict[str, Any], str]:
    """Load one bounded regular JSON file and return it plus its byte hash."""
    if path.is_symlink():
        raise BridgeError(f"input is a symlink: {path}")
    if not path.is_file():
        raise BridgeError(f"input is not a regular file: {path}")
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise BridgeError(f"input exceeds {MAX_JSON_BYTES} bytes: {path}")
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BridgeError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BridgeError(f"top-level JSON value must be an object: {path}")
    return value, hashlib.sha256(raw).hexdigest()


def _require_keys(value: dict[str, Any], required: set[str], allowed: set[str], where: str) -> None:
    missing = sorted(required - value.keys())
    extra = sorted(value.keys() - allowed)
    if missing:
        raise BridgeError(f"{where} missing keys: {', '.join(missing)}")
    if extra:
        raise BridgeError(f"{where} has unknown keys: {', '.join(extra)}")


def _require_string(value: Any, where: str, *, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise BridgeError(f"{where} must be a non-empty string of at most {maximum} characters")
    if "\x00" in value or "\n" in value or "\r" in value:
        raise BridgeError(f"{where} contains a forbidden control character")
    return value


def _validate_hash(value: Any, where: str, regex: re.Pattern[str]) -> str:
    if not isinstance(value, str) or regex.fullmatch(value) is None:
        raise BridgeError(f"{where} has an invalid lowercase hexadecimal identity")
    return value


def _validate_relative_path(value: Any, where: str) -> str:
    path = _require_string(value, where, maximum=500)
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or "\\" in path or ":" in path:
        raise BridgeError(f"{where} must be a safe repository-relative POSIX path")
    if path.startswith("-") or path.endswith("/"):
        raise BridgeError(f"{where} is not a valid repository file path")
    return path


def _validate_binary(value: Any, where: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise BridgeError(f"{where} must be an object")
    _require_keys(value, {"id", "sha256", "architecture"}, {"id", "sha256", "architecture"}, where)
    return {
        "id": _require_string(value["id"], f"{where}.id", maximum=100),
        "sha256": _validate_hash(value["sha256"], f"{where}.sha256", SHA256_RE),
        "architecture": _require_string(value["architecture"], f"{where}.architecture", maximum=64),
    }


def _validate_locator(value: Any, where: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise BridgeError(f"{where} must be an object")
    _require_keys(value, {"kind", "value"}, {"kind", "value"}, where)
    kind = _require_string(value["kind"], f"{where}.kind", maximum=32)
    if kind not in LOCATOR_KINDS:
        raise BridgeError(f"{where}.kind is not supported: {kind}")
    locator = _require_string(value["value"], f"{where}.value", maximum=100)
    return {"kind": kind, "value": locator}


def _validate_evidence(value: Any, where: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise BridgeError(f"{where} must be a non-empty array")
    result = []
    seen = set()
    for index, item in enumerate(value):
        item_where = f"{where}[{index}]"
        if not isinstance(item, dict):
            raise BridgeError(f"{item_where} must be an object")
        _require_keys(item, {"path", "blob_sha256"}, {"path", "blob_sha256"}, item_where)
        row = {
            "path": _validate_relative_path(item["path"], f"{item_where}.path"),
            "blob_sha256": _validate_hash(item["blob_sha256"], f"{item_where}.blob_sha256", SHA256_RE),
        }
        identity = (row["path"], row["blob_sha256"])
        if identity in seen:
            raise BridgeError(f"{where} contains a duplicate evidence row")
        seen.add(identity)
        result.append(row)
    return result


def _validate_attributes(value: Any, where: str) -> dict[str, str | int | bool]:
    if not isinstance(value, dict) or not value or len(value) > 16:
        raise BridgeError(f"{where} must contain 1..16 scalar attributes")
    result: dict[str, str | int | bool] = {}
    for key, item in value.items():
        if not isinstance(key, str) or ATTRIBUTE_KEY_RE.fullmatch(key) is None:
            raise BridgeError(f"{where} has an invalid attribute key: {key!r}")
        if isinstance(item, bool):
            result[key] = item
        elif isinstance(item, int) and not isinstance(item, bool):
            if abs(item) > 0xFFFFFFFFFFFFFFFF:
                raise BridgeError(f"{where}.{key} integer is outside the supported 64-bit magnitude")
            result[key] = item
        elif isinstance(item, str):
            result[key] = _require_string(item, f"{where}.{key}", maximum=200)
        else:
            raise BridgeError(f"{where}.{key} must be a string, integer, or boolean")
    return result


def _feature_identity(feature: dict[str, Any]) -> str:
    identity = {
        "attributes": feature["attributes"],
        "kind": feature["kind"],
        "semantic": feature["semantic"],
    }
    return json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _validate_feature(value: Any, where: str, *, weighted: bool) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BridgeError(f"{where} must be an object")
    required = {"kind", "semantic", "attributes"}
    allowed = set(required)
    if weighted:
        required |= {"weight", "required"}
        allowed |= {"weight", "required"}
    _require_keys(value, required, allowed, where)
    kind = _require_string(value["kind"], f"{where}.kind", maximum=64)
    if kind not in FEATURE_KINDS:
        raise BridgeError(f"{where}.kind is not supported: {kind}")
    semantic = _require_string(value["semantic"], f"{where}.semantic", maximum=96)
    if SEMANTIC_RE.fullmatch(semantic) is None:
        raise BridgeError(f"{where}.semantic is not normalized")
    result: dict[str, Any] = {
        "kind": kind,
        "semantic": semantic,
        "attributes": _validate_attributes(value["attributes"], f"{where}.attributes"),
    }
    if weighted:
        weight = value["weight"]
        required_flag = value["required"]
        if not isinstance(weight, int) or isinstance(weight, bool) or not 1 <= weight <= 100:
            raise BridgeError(f"{where}.weight must be an integer from 1 through 100")
        if not isinstance(required_flag, bool):
            raise BridgeError(f"{where}.required must be boolean")
        result.update(weight=weight, required=required_flag)
    return result


def _validate_features(value: Any, where: str, *, weighted: bool, maximum: int) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise BridgeError(f"{where} must contain 1..{maximum} features")
    result = []
    seen = set()
    for index, item in enumerate(value):
        feature = _validate_feature(item, f"{where}[{index}]", weighted=weighted)
        identity = _feature_identity(feature)
        if identity in seen:
            raise BridgeError(f"{where} contains a duplicate normalized feature")
        seen.add(identity)
        result.append(feature)
    return result


def _validate_string_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise BridgeError(f"{where} must be a non-empty array")
    result = [_require_string(item, f"{where}[{index}]", maximum=500) for index, item in enumerate(value)]
    if len(set(result)) != len(result):
        raise BridgeError(f"{where} contains duplicate values")
    return result


def validate_lead(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema", "lead_id", "direction", "status", "purpose", "source",
        "target", "question", "signature", "nonclaims", "verification_required",
    }
    _require_keys(value, required, required, "lead")
    if value["schema"] != LEAD_SCHEMA:
        raise BridgeError(f"lead.schema must be {LEAD_SCHEMA}")
    lead_id = _require_string(value["lead_id"], "lead.lead_id", maximum=104)
    if LEAD_ID_RE.fullmatch(lead_id) is None:
        raise BridgeError("lead.lead_id is not a normalized PC2PS1 identifier")
    if value["direction"] != "pc-to-ps1":
        raise BridgeError("this ABL consumer accepts only pc-to-ps1 leads")
    if value["status"] != "external_lead":
        raise BridgeError("cross-port input may only enter ABL as external_lead")
    if value["purpose"] not in {"calibration", "discovery"}:
        raise BridgeError("lead.purpose must be calibration or discovery")

    source = value["source"]
    if not isinstance(source, dict):
        raise BridgeError("lead.source must be an object")
    _require_keys(
        source,
        {"project", "repository_commit", "binary", "locator", "evidence"},
        {"project", "repository_commit", "binary", "locator", "evidence"},
        "lead.source",
    )
    if source["project"] != "ABLPC":
        raise BridgeError("lead.source.project must be ABLPC")
    source_commit = _validate_hash(source["repository_commit"], "lead.source.repository_commit", COMMIT_RE)
    source_binary = _validate_binary(source["binary"], "lead.source.binary")
    if source_binary["architecture"] != PC_ARCHITECTURE:
        raise BridgeError(f"lead source architecture must be {PC_ARCHITECTURE}")

    target = value["target"]
    if not isinstance(target, dict):
        raise BridgeError("lead.target must be an object")
    _require_keys(target, {"project", "binary"}, {"project", "binary"}, "lead.target")
    if target["project"] != "ABL":
        raise BridgeError("lead.target.project must be ABL")
    target_binary = _validate_binary(target["binary"], "lead.target.binary")
    if target_binary != {
        "id": PS1_BINARY_ID,
        "sha256": PS1_BINARY_SHA256,
        "architecture": PS1_ARCHITECTURE,
    }:
        raise BridgeError("lead target does not match the pinned pristine PS1 executable")

    signature = value["signature"]
    if not isinstance(signature, dict):
        raise BridgeError("lead.signature must be an object")
    _require_keys(signature, {"normal_form", "features"}, {"normal_form", "features"}, "lead.signature")
    if signature["normal_form"] != NORMAL_FORM:
        raise BridgeError(f"lead.signature.normal_form must be {NORMAL_FORM}")

    return {
        **value,
        "source": {
            **source,
            "repository_commit": source_commit,
            "binary": source_binary,
            "locator": _validate_locator(source["locator"], "lead.source.locator"),
            "evidence": _validate_evidence(source["evidence"], "lead.source.evidence"),
        },
        "target": {"project": "ABL", "binary": target_binary},
        "question": _require_string(value["question"], "lead.question", maximum=1000),
        "signature": {
            "normal_form": NORMAL_FORM,
            "features": _validate_features(signature["features"], "lead.signature.features", weighted=True, maximum=128),
        },
        "nonclaims": _validate_string_list(value["nonclaims"], "lead.nonclaims"),
        "verification_required": _validate_string_list(
            value["verification_required"], "lead.verification_required"
        ),
    }


def validate_catalog(value: dict[str, Any]) -> dict[str, Any]:
    required = {"schema", "status", "repository_commit", "target", "candidates"}
    _require_keys(value, required, required, "catalog")
    if value["schema"] != CATALOG_SCHEMA:
        raise BridgeError(f"catalog.schema must be {CATALOG_SCHEMA}")
    if value["status"] != "curated_calibration_catalog":
        raise BridgeError("pilot catalogs must be explicitly curated_calibration_catalog")
    repository_commit = _validate_hash(value["repository_commit"], "catalog.repository_commit", COMMIT_RE)
    target = value["target"]
    if not isinstance(target, dict):
        raise BridgeError("catalog.target must be an object")
    _require_keys(target, {"project", "binary"}, {"project", "binary"}, "catalog.target")
    if target["project"] != "ABL":
        raise BridgeError("catalog.target.project must be ABL")
    binary = _validate_binary(target["binary"], "catalog.target.binary")
    if binary != {
        "id": PS1_BINARY_ID,
        "sha256": PS1_BINARY_SHA256,
        "architecture": PS1_ARCHITECTURE,
    }:
        raise BridgeError("catalog target does not match the pinned pristine PS1 executable")

    raw_candidates = value["candidates"]
    if not isinstance(raw_candidates, list) or not 1 <= len(raw_candidates) <= 10000:
        raise BridgeError("catalog.candidates must contain 1..10000 candidates")
    candidates = []
    ids = set()
    for index, item in enumerate(raw_candidates):
        where = f"catalog.candidates[{index}]"
        if not isinstance(item, dict):
            raise BridgeError(f"{where} must be an object")
        _require_keys(
            item,
            {"candidate_id", "locator", "evidence", "features"},
            {"candidate_id", "locator", "evidence", "features"},
            where,
        )
        candidate_id = _require_string(item["candidate_id"], f"{where}.candidate_id", maximum=104)
        if CANDIDATE_ID_RE.fullmatch(candidate_id) is None:
            raise BridgeError(f"{where}.candidate_id is not normalized")
        if candidate_id in ids:
            raise BridgeError(f"duplicate candidate_id: {candidate_id}")
        ids.add(candidate_id)
        candidates.append({
            "candidate_id": candidate_id,
            "locator": _validate_locator(item["locator"], f"{where}.locator"),
            "evidence": _validate_evidence(item["evidence"], f"{where}.evidence"),
            "features": _validate_features(item["features"], f"{where}.features", weighted=False, maximum=256),
        })
    return {
        "schema": CATALOG_SCHEMA,
        "status": "curated_calibration_catalog",
        "repository_commit": repository_commit,
        "target": {"project": "ABL", "binary": binary},
        "candidates": candidates,
    }


def _git_bytes(repository: Path, commit: str, path: str) -> bytes:
    try:
        resolved = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "--verify", f"{commit}^{{commit}}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if resolved != commit:
            raise BridgeError(f"repository commit resolved unexpectedly: {resolved}")
        return subprocess.run(
            ["git", "-C", str(repository), "show", f"{commit}:{path}"],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BridgeError(f"cannot read committed evidence {commit}:{path} from {repository}") from exc


def verify_committed_evidence(repository: Path, commit: str, evidence: list[dict[str, str]]) -> None:
    """Hash evidence from committed blobs only; never consult the working tree."""
    if not repository.is_dir():
        raise BridgeError(f"repository does not exist: {repository}")
    for row in evidence:
        actual = hashlib.sha256(_git_bytes(repository, commit, row["path"])).hexdigest()
        if actual != row["blob_sha256"]:
            raise BridgeError(
                f"committed evidence hash mismatch for {commit}:{row['path']}: "
                f"expected {row['blob_sha256']}, got {actual}"
            )


def verify_catalog_evidence(repository: Path, catalog: dict[str, Any]) -> None:
    evidence_by_identity: dict[tuple[str, str], dict[str, str]] = {}
    for candidate in catalog["candidates"]:
        for row in candidate["evidence"]:
            evidence_by_identity[(row["path"], row["blob_sha256"])] = row
    verify_committed_evidence(repository, catalog["repository_commit"], list(evidence_by_identity.values()))


def verify_binary(path: Path, expected_sha256: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise BridgeError(f"binary is not a regular non-symlink file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected_sha256:
        raise BridgeError(f"binary hash mismatch for {path}: expected {expected_sha256}, got {actual}")


def rank_candidates(
    lead: dict[str, Any],
    catalog: dict[str, Any],
    *,
    lead_sha256: str,
    catalog_sha256: str,
) -> dict[str, Any]:
    if lead["target"] != catalog["target"]:
        raise BridgeError("lead and catalog target identities differ")
    lead_features = lead["signature"]["features"]
    total_weight = sum(feature["weight"] for feature in lead_features)
    if total_weight <= 0:
        raise BridgeError("lead feature weight is empty")
    lead_by_identity = {_feature_identity(feature): feature for feature in lead_features}
    required = {
        identity for identity, feature in lead_by_identity.items() if feature["required"]
    }

    ranked = []
    for candidate in catalog["candidates"]:
        candidate_identities = {_feature_identity(feature) for feature in candidate["features"]}
        matched = sorted(set(lead_by_identity) & candidate_identities)
        missing_required = sorted(required - candidate_identities)
        matched_weight = sum(lead_by_identity[identity]["weight"] for identity in matched)
        raw_bps = (matched_weight * 10000 + total_weight // 2) // total_weight
        eligible = not missing_required
        score_bps = raw_bps if eligible else raw_bps // 2
        ranked.append({
            "candidate_id": candidate["candidate_id"],
            "locator": candidate["locator"],
            "eligible": eligible,
            "score_basis_points": score_bps,
            "raw_coverage_basis_points": raw_bps,
            "matched_weight": matched_weight,
            "total_weight": total_weight,
            "matched_features": [json.loads(identity) for identity in matched],
            "missing_required_features": [json.loads(identity) for identity in missing_required],
            "candidate_evidence": candidate["evidence"],
            "claim_status": "ps1_candidate_only",
        })
    ranked.sort(key=lambda row: (not row["eligible"], -row["score_basis_points"], row["candidate_id"]))
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index

    return {
        "schema": RESULT_SCHEMA,
        "status": "ranked_external_leads_only",
        "lead_id": lead["lead_id"],
        "lead_purpose": lead["purpose"],
        "lead_packet_sha256": lead_sha256,
        "candidate_catalog_sha256": catalog_sha256,
        "source": lead["source"],
        "target": lead["target"],
        "catalog_repository_commit": catalog["repository_commit"],
        "normal_form": NORMAL_FORM,
        "ranking_method": "exact-feature-weighted-coverage-v1; missing-required penalty=0.5",
        "candidate_count": len(ranked),
        "candidates": ranked,
        "nonclaims": lead["nonclaims"],
        "verification_required": lead["verification_required"],
        "promotion_allowed": False,
    }


def _write_new(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise BridgeError(f"refusing to overwrite output: {path}")
    parent = path.parent.resolve()
    if not parent.is_dir():
        raise BridgeError(f"output parent does not exist: {parent}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o644)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _load_and_validate_lead(path: Path) -> tuple[dict[str, Any], str]:
    raw, digest = load_json_strict(path)
    return validate_lead(raw), digest


def _load_and_validate_catalog(path: Path) -> tuple[dict[str, Any], str]:
    raw, digest = load_json_strict(path)
    return validate_catalog(raw), digest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    lead = sub.add_parser("validate-lead", help="validate one inbound lead")
    lead.add_argument("lead", type=Path)
    lead.add_argument("--source-repo", type=Path, help="verify evidence from this pinned Git repository")

    catalog = sub.add_parser("validate-catalog", help="validate one PS1 candidate catalog")
    catalog.add_argument("catalog", type=Path)
    catalog.add_argument("--target-repo", type=Path, help="verify evidence from this pinned Git repository")
    catalog.add_argument("--target-binary", type=Path, help="verify the pristine PS1 executable hash")

    rank = sub.add_parser("rank", help="rank PS1 candidates for one inbound PC lead")
    rank.add_argument("lead", type=Path)
    rank.add_argument("catalog", type=Path)
    rank.add_argument("--source-repo", type=Path)
    rank.add_argument("--target-repo", type=Path)
    rank.add_argument("--target-binary", type=Path)
    rank.add_argument("--output", type=Path, help="write a new result file; existing paths are refused")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "validate-lead":
            lead, digest = _load_and_validate_lead(args.lead)
            if args.source_repo:
                verify_committed_evidence(
                    args.source_repo, lead["source"]["repository_commit"], lead["source"]["evidence"]
                )
            print(json.dumps({"status": "valid-external-lead", "lead_id": lead["lead_id"], "sha256": digest}, sort_keys=True))
            return 0

        if args.command == "validate-catalog":
            catalog, digest = _load_and_validate_catalog(args.catalog)
            if args.target_repo:
                verify_catalog_evidence(args.target_repo, catalog)
            if args.target_binary:
                verify_binary(args.target_binary, PS1_BINARY_SHA256)
            print(json.dumps({"status": "valid-curated-catalog", "candidate_count": len(catalog["candidates"]), "sha256": digest}, sort_keys=True))
            return 0

        lead, lead_digest = _load_and_validate_lead(args.lead)
        catalog, catalog_digest = _load_and_validate_catalog(args.catalog)
        if args.source_repo:
            verify_committed_evidence(
                args.source_repo, lead["source"]["repository_commit"], lead["source"]["evidence"]
            )
        if args.target_repo:
            verify_catalog_evidence(args.target_repo, catalog)
        if args.target_binary:
            verify_binary(args.target_binary, PS1_BINARY_SHA256)
        result = rank_candidates(
            lead,
            catalog,
            lead_sha256=lead_digest,
            catalog_sha256=catalog_digest,
        )
        rendered = _json_bytes(result)
        if args.output:
            _write_new(args.output, rendered)
        else:
            sys.stdout.buffer.write(rendered)
        return 0
    except BridgeError as exc:
        print(f"cross-port bridge: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

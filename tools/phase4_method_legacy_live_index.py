#!/usr/bin/env python3
"""Build the conservative pre-v2 Phase-4 live-experiment deny index."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "analysis" / "phase4_live_escalations.json"
OUTPUT = ROOT / "analysis" / "phase4_method_legacy_live_index.json"
SCHEMA = "abl-phase4-method-legacy-live-index/2"
SOURCE_PROJECTION = "exclude-derived-post-run-audit/1"
INDEX_CREATED = "2026-07-26"
BASELINE_SOURCE_SHA256 = (
    "85389686203016b7748be4fbed32b8b8782d87c07c643fad76eb620a83bb19c3"
)
LEGACY_IDS = (
    "P4-ITER69-A11-MISSING-CAPSULE",
    "P4-ITER69-A10-MISSING-CAPSULE",
    "P4-ITER70-C18-MISSING-CAPSULE",
    "P4-ITER70-F16-MISSING-CAPSULE",
    "P4-ITER70-F17-MISSING-CAPSULE",
    "P4-ITER70-F18-MISSING-CAPSULE",
    "P4-ITER79-E15-CALLBACK-TEARDOWN-CONTROL",
    "P4-ITER81-E15-NATURAL-LEVELA-COMPLETION-CONTROL",
    "P4-ITER82-E15-NATURAL-EXIT-CAUSE-CONTROL",
    "P4-ITER83-E15-LOSE-GAMEOVER-LIFECYCLE-CONTROL",
    "P4-ITER86-E15-LEVELB-LIFECYCLE-CONTROL",
    "P4-ITER87-E15-LEVELB-SAVE-ANCHOR-CONTROL",
    "P4-ITER88-E15-LEVELB-PHASE-NEUTRAL-REVALIDATION",
    "P4-ITER89-E15-LEVELB-FIRST-CALL-LIFECYCLE",
    "P4-ITER90-E15-FINALE-SEQUENCE-LIFECYCLE",
    "P4-ITER91-E15-FINALE-ENDPOINT-CORRECTION",
)
LEVELB_NORMALIZATION_IDS = {
    "P4-ITER86-E15-LEVELB-LIFECYCLE-CONTROL",
    "P4-ITER87-E15-LEVELB-SAVE-ANCHOR-CONTROL",
    "P4-ITER88-E15-LEVELB-PHASE-NEUTRAL-REVALIDATION",
    "P4-ITER89-E15-LEVELB-FIRST-CALL-LIFECYCLE",
}


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def source_projection(raw: dict[str, Any]) -> dict[str, Any]:
    """Pin historical evidence while excluding the regenerated current audit."""
    return {
        key: value for key, value in raw.items()
        if key != "derived_post_run_audit"
    }


def source_entry_sha256(raw: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(source_projection(raw))).hexdigest()


def _method_values(value: Any):
    if isinstance(value, dict):
        method = value.get("method")
        if isinstance(method, str):
            yield method
        for child in value.values():
            yield from _method_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _method_values(child)


def normalized_observer_basis(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Derive a bounded non-DMA domain only from hash-pinned retained results."""
    if raw.get("id") not in LEVELB_NORMALIZATION_IDS:
        return None
    external = (raw.get("execution_result") or {}).get("external_receipts")
    if not isinstance(external, list) or not external:
        return None
    methods: set[str] = set()
    digests: list[str] = []
    for spec in external:
        if not isinstance(spec, dict) or set(spec) != {
                "absolute_path", "bytes", "sha256"}:
            return None
        path = Path(spec["absolute_path"])
        if not path.is_absolute() or not path.is_file() or \
                path.stat().st_size != spec["bytes"] or \
                hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
            return None
        digests.append(spec["sha256"])
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        methods.update(_method_values(document))
    observer_methods = sorted(
        method for method in methods
        if method.startswith((
            "accessLog.", "execTrace.", "functionTrace.",
            "movie.traceToFrame", "provenanceLog.", "transferLog.",
        ))
    )
    if not observer_methods or any(
            method.startswith("transferLog.") for method in observer_methods):
        return None
    return {
        "normalization": "normalized",
        "domain": "interface",
        "observer_methods": observer_methods,
        "external_receipt_sha256s": sorted(set(digests)),
    }


def build() -> dict[str, Any]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    entries = []
    by_id = {entry.get("id"): entry for entry in source.get("entries") or []}
    for escalation_id in LEGACY_IDS:
        raw = by_id.get(escalation_id, {})
        result = raw.get("execution_result") or {}
        media = result.get("media") or {}
        normalized = normalized_observer_basis(raw)
        entries.append({
            "escalation_id": raw.get("id"),
            "target_row": raw.get("target_row"),
            "state": raw.get("state"),
            "normalization": (
                normalized["normalization"]
                if normalized is not None else "conservative_deny"
            ),
            "media_sha256": media.get("bin_sha256"),
            "movie_sha256": media.get("movie_sha256"),
            "state_sha256": media.get("state_sha256"),
            "domain": normalized["domain"] if normalized is not None else None,
            "window": None,
            "observer_methods": (
                normalized["observer_methods"] if normalized is not None else []
            ),
            "external_receipt_sha256s": (
                normalized["external_receipt_sha256s"]
                if normalized is not None else []
            ),
            "source_entry_sha256": source_entry_sha256(raw),
        })
    return {
        "schema": SCHEMA,
        # This is the creation date of the immutable pre-v2 cutoff, not the
        # wall-clock date of a freshness check. A current date here makes an
        # otherwise unchanged retained index turn stale at every midnight.
        "generated": INDEX_CREATED,
        "source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "baseline_sha256": BASELINE_SOURCE_SHA256,
            "projection": SOURCE_PROJECTION,
            "legacy_ids": list(LEGACY_IDS),
        },
        "entries": entries,
        "counts": {
            "entries": len(entries),
            "normalized": sum(
                row["normalization"] == "normalized" for row in entries),
            "conservative_deny": sum(
                row["normalization"] == "conservative_deny"
                for row in entries),
        },
        "complete": all(
            isinstance(item["escalation_id"], str) and
            isinstance(item["target_row"], str)
            for item in entries
        ),
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = build()
    if args.write:
        OUTPUT.write_text(json.dumps(generated, indent=2) + "\n",
                          encoding="utf-8")
    if args.check:
        if not OUTPUT.is_file():
            print("FAIL: legacy live index is missing")
            return 1
        retained = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if retained != generated:
            print("FAIL: legacy live index is stale")
            return 1
    if not generated["complete"] or generated["errors"]:
        print("FAIL: legacy live index is incomplete")
        return 1
    print(
        f"PASS: {generated['counts']['entries']} pre-v2 live entries "
        f"({generated['counts']['normalized']} normalized, "
        f"{generated['counts']['conservative_deny']} conservative deny)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

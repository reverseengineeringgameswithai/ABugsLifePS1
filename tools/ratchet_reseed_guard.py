#!/usr/bin/env python3
"""Progress-sensitive circuit breaker for Phase-4 automatic trial reseeds."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SCHEMA = "abl-phase4-reseed-guard/1"
_VOLATILE_PATH = re.compile(
    r"(?:/[\w.@+-]+)+/(?:runs|worktrees)/phase4-[^\s:]+"
)
_ITERATION = re.compile(r"iteration-\d+")
_COMMIT = re.compile(r"\b[0-9a-f]{40}\b")


def _load_json(path: Path | None) -> Any:
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _decision_projection(path: Path | None) -> dict[str, Any] | None:
    value = _load_json(path)
    if not isinstance(value, dict):
        return None
    return {
        key: value.get(key)
        for key in (
            "phase",
            "status",
            "summary",
            "gaps",
            "gap_codes",
            "required_input",
        )
    }


def _debt_projection(path: Path | None) -> dict[str, Any] | None:
    value = _load_json(path)
    if not isinstance(value, dict):
        return None
    campaigns = []
    for row in value.get("campaigns", []):
        if not isinstance(row, dict):
            continue
        campaigns.append({
            "campaign_id": row.get("campaign_id"),
            "counts": row.get("counts"),
            "dimensions": row.get("dimensions"),
            "next_lane": row.get("next_lane"),
            "rows": row.get("rows"),
        })
    scheduler = value.get("scheduler")
    if isinstance(scheduler, dict):
        scheduler = {
            "selected_campaigns": scheduler.get("selected_campaigns"),
            "wip_limits": scheduler.get("wip_limits"),
        }
    return {
        "valid": value.get("valid"),
        "counts": value.get("counts"),
        "campaigns": campaigns,
        "scheduler": scheduler,
    }


def _normalise_text(value: str) -> str:
    value = _VOLATILE_PATH.sub("$RUN_PATH", value)
    value = _ITERATION.sub("iteration-N", value)
    value = _COMMIT.sub("$COMMIT", value)
    return value


def _details_projection(path: Path | None) -> Any:
    value = _load_json(path)
    if isinstance(value, dict):
        return {
            key: value.get(key)
            for key in (
                "schema",
                "complete",
                "errors",
                "reseed_required",
                "trial_critical_paths",
            )
            if key in value
        }
    if path is None or not path.is_file():
        return None
    try:
        # Failure details can be multi-megabyte logs. A bounded tail preserves the
        # terminal signature without hashing volatile transcript bulk.
        raw = path.read_bytes()
        text = raw[-8192:].decode("utf-8", errors="replace")
    except OSError:
        return None
    return _normalise_text(text)


def build(
    *,
    reason: str,
    decision: Path | None,
    debt: Path | None,
    details: Path | None,
    previous_signature: str,
    previous_repeat_count: int,
    max_identical_reseeds: int,
) -> dict[str, Any]:
    payload = {
        "reason": reason,
        "decision": _decision_projection(decision),
        "debt": _debt_projection(debt),
        "details": _details_projection(details),
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    signature = hashlib.sha256(encoded).hexdigest()
    repeated = bool(previous_signature) and signature == previous_signature
    repeat_count = previous_repeat_count + 1 if repeated else 1
    return {
        "schema": SCHEMA,
        "semantic_signature": signature,
        "previous_signature": previous_signature or None,
        "same_as_previous": repeated,
        "repeat_count": repeat_count,
        "max_identical_reseeds": max_identical_reseeds,
        "circuit_open": repeat_count >= max_identical_reseeds,
        "payload": payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--debt", type=Path)
    parser.add_argument("--details", type=Path)
    parser.add_argument("--previous-signature", default="")
    parser.add_argument("--previous-repeat-count", type=int, default=0)
    parser.add_argument("--max-identical-reseeds", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.previous_repeat_count < 0:
        parser.error("--previous-repeat-count must be non-negative")
    if args.max_identical_reseeds < 2:
        parser.error("--max-identical-reseeds must be at least 2")
    if args.previous_signature and not re.fullmatch(
        r"[0-9a-f]{64}", args.previous_signature
    ):
        parser.error("--previous-signature must be an empty or lowercase SHA-256")
    document = build(
        reason=args.reason,
        decision=args.decision,
        debt=args.debt,
        details=args.details,
        previous_signature=args.previous_signature,
        previous_repeat_count=args.previous_repeat_count,
        max_identical_reseeds=args.max_identical_reseeds,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    state = "OPEN" if document["circuit_open"] else "CONTINUE"
    print(
        f"PASS: reseed guard {state}; repeat={document['repeat_count']}/"
        f"{document['max_identical_reseeds']} "
        f"signature={document['semantic_signature']}"
    )
    return 2 if document["circuit_open"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

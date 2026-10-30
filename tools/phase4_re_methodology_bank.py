#!/usr/bin/env python3
"""Bank an independently accepted Phase-4 RE methodology verdict in Obsidian."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


START = "<!-- PHASE4_METHODOLOGY_RATCHET_VERDICT_START -->"
END = "<!-- PHASE4_METHODOLOGY_RATCHET_VERDICT_END -->"


def _one_line(value: str) -> str:
    return " ".join(value.split())


def _bullets(values: list[str]) -> str:
    return "\n".join(f"- {_one_line(value)}" for value in values) or "- None."


def bank(
    note_path: Path,
    verdict_path: Path,
    *,
    run_id: str,
    verified_at: str,
) -> None:
    verdict_bytes = verdict_path.read_bytes()
    verdict = json.loads(verdict_bytes)
    if verdict.get("role") != "hard_truth_verifier":
        raise ValueError("verdict role is not hard_truth_verifier")
    if verdict.get("status") != "accepted":
        raise ValueError("only an accepted verdict may be banked")
    if verdict.get("gaps") or str(verdict.get("required_input", "")).strip():
        raise ValueError("accepted verdict cannot contain gaps or required_input")

    note = note_path.read_text(encoding="utf-8")
    if note.count("status: candidate") != 1:
        raise ValueError("note must contain exactly one candidate status")
    if note.count("methodology_ratchet: pending") != 1:
        raise ValueError("note must contain exactly one pending ratchet status")
    if note.count(START) != 1 or note.count(END) != 1:
        raise ValueError("note must contain exactly one verdict marker block")
    start = note.index(START)
    end = note.index(END, start) + len(END)

    receipt = f"""\
{START}
### Independent hard-truth acceptance

- **Status:** accepted
- **Verified:** {verified_at}
- **Ratchet run:** `{run_id}`
- **Reviewed candidate:** `{verdict["reviewed_commit"]}`
- **Verifier decision SHA-256:** `{hashlib.sha256(verdict_bytes).hexdigest()}`

**Verifier conclusion:** {_one_line(verdict["summary"])}

**Evidence independently inspected**

{_bullets(verdict["evidence"])}

**Validation and falsification attempts**

{_bullets(verdict["validation"])}

This receipt accepts the operating method only. It does not close Phase 4 or promote
any gameplay finding.
{END}"""

    banked = note[:start] + receipt + note[end:]
    banked = banked.replace("status: candidate", "status: accepted", 1)
    banked = banked.replace(
        "methodology_ratchet: pending", "methodology_ratchet: verified", 1
    )
    note_path.write_text(banked, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--note", type=Path, required=True)
    parser.add_argument("--verdict", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--verified-at", required=True)
    args = parser.parse_args()
    bank(
        args.note,
        args.verdict,
        run_id=args.run_id,
        verified_at=args.verified_at,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

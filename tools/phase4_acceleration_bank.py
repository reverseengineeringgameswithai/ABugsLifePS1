#!/usr/bin/env python3
"""Bank an accepted Phase-4 acceleration hard-truth decision into its note."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
NOTE = ROOT / "ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Acceleration Tooling Strategy.md"
START = "<!-- PHASE4_ACCELERATION_RATCHET_VERDICT_START -->"
END = "<!-- PHASE4_ACCELERATION_RATCHET_VERDICT_END -->"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_decision(decision: dict, reviewed_commit: str) -> None:
    if decision.get("schema") != "abl-phase4-acceleration-hard-truth-decision/1":
        raise ValueError("invalid hard-truth decision schema")
    if decision.get("verdict") != "accepted":
        raise ValueError("only an accepted hard-truth decision may be banked")
    if decision.get("gaps") != [] or decision.get("required_inputs") != []:
        raise ValueError("accepted decision must have empty gaps and required_inputs")
    if decision.get("reviewed_commit") != reviewed_commit:
        raise ValueError("decision reviewed_commit differs from the requested commit")
    if not re.fullmatch(r"[0-9a-f]{40}", reviewed_commit):
        raise ValueError("reviewed commit must be a full Git object ID")
    for key in ("run_id", "verified_at", "conclusion"):
        if not str(decision.get(key) or "").strip():
            raise ValueError(f"decision lacks {key}")


def bank_text(text: str, decision: dict, decision_sha256: str) -> str:
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("acceleration verdict markers must occur exactly once")
    text, status_count = re.subn(r"(?m)^status: candidate$", "status: accepted", text)
    text, ratchet_count = re.subn(
        r"(?m)^acceleration_ratchet: pending$", "acceleration_ratchet: accepted", text)
    if status_count != 1 or ratchet_count != 1:
        raise ValueError("candidate frontmatter is absent or already banked")
    verdict = (
        f"{START}\n"
        f"Hard-truth accepted. Run `{decision['run_id']}` reviewed commit "
        f"`{decision['reviewed_commit']}` at {decision['verified_at']}. "
        f"Conclusion: {decision['conclusion']} Decision SHA-256: "
        f"`{decision_sha256}`.\n"
        f"{END}"
    )
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    return pattern.sub(verdict, text, count=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--reviewed-commit", required=True)
    args = parser.parse_args()
    decision_path = args.decision.resolve()
    try:
        decision_path.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("hard-truth decision must remain external to the repository")
    decision = json.loads(decision_path.read_text())
    validate_decision(decision, args.reviewed_commit)
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        capture_output=True, check=True).stdout.strip()
    if current_head != args.reviewed_commit:
        raise ValueError("banking worktree is not at the reviewed commit")
    before = NOTE.read_text()
    after = bank_text(before, decision, sha256(decision_path))
    NOTE.write_text(after)
    print(f"[phase4-acceleration-bank] banked {decision['run_id']} for {current_head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

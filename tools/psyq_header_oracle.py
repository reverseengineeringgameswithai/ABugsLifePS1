#!/usr/bin/env python3
"""Hash owner-supplied PsyQ headers without copying them into the repository."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from substrate_common import external_header_evidence  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("include_dir", nargs="?", help="defaults to $ABL_PSYQ_INCLUDE")
    parser.add_argument("--output", type=Path,
                        help="optional local JSON output (do not commit original headers)")
    args = parser.parse_args()
    value = args.include_dir or os.environ.get("ABL_PSYQ_INCLUDE")
    if not value:
        parser.error("provide include_dir or set ABL_PSYQ_INCLUDE")
    evidence = external_header_evidence(Path(value).expanduser().resolve())
    payload = json.dumps(evidence, indent=1) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="ascii")
        print(f"wrote hash-only oracle evidence: {args.output}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

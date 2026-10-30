#!/usr/bin/env python3
"""Readability guard: reject machine-tangled permuter output before banking.

`tools/dc_permute.py` produces readable rewrites, but the upstream driver
(`dc_permute_upstream.py`) / a bad edit can leave junk that byte-matches yet is not
readable C. This guard flags the tangle signatures so tangled sources never get
banked. Exit 0 = readable, exit 1 = tangled (prints the offending markers).

  python tools/dc_readable.py <src.c>          # check a file
  from dc_readable import is_readable            # or import the predicate
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# tangle signatures the upstream randomizer injects (and that a hand-authored /
# dc_permute.py source would never contain)
_MARKERS = [
    (r"\bnew_var\w*", "permuter temp `new_var`"),
    (r"\bdummy_label\w*", "permuter `dummy_label`"),
    (r"\^\s*0\b", "no-op `^ 0`"),
    (r"\(\s*0\s*,", "comma no-op `(0, ...)`"),
    (r"do\s*\{\s*\}\s*while\s*\(\s*0\s*\)", "empty `do {} while (0)`"),
    (r"0xFFFFFFFFFFFFFFFF", "64-bit all-ones junk mask"),
    (r"-\s*\(\s*-0\s*\)", "no-op `- (-0)`"),
]


def is_readable(src: str) -> tuple[bool, list[str]]:
    """Return (readable, reasons). Also flags an absurd local-decl count (>~20
    scalar decls in one function ~ never hand-written)."""
    reasons = []
    for pat, why in _MARKERS:
        if re.search(pat, src):
            reasons.append(why)
    n_semi_empty = len(re.findall(r"^\s*;\s*$", src, re.MULTILINE))
    if n_semi_empty > 3:
        reasons.append(f"{n_semi_empty} empty statements")
    n_decls = len(re.findall(r"^\s*(?:unsigned |signed )?(?:int|short|char|long)\b[^=(]*;",
                             src, re.MULTILINE))
    if n_decls > 20:
        reasons.append(f"{n_decls} bare local declarations")
    return (not reasons), reasons


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__); return 2
    src = Path(sys.argv[1]).read_text()
    ok, reasons = is_readable(src)
    if ok:
        print("readable")
        return 0
    print("TANGLED — not bankable:\n  " + "\n  ".join(reasons))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

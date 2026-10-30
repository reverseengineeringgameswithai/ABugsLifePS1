"""Guard the compiler flag-matrix log (analysis/compiler_attempts.json).

CI-safe: validates the committed attempts record — schema, that every shipped
C entry has a recorded match, that the winning flags equal the pinned
c_toolchain, and that no (function, source, declaration profile, compiler,
flags, maspsx) combo is duplicated
(so re-runs update rather than pile up). No compiler needed.
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
ATTEMPTS = ROOT / "analysis" / "compiler_attempts.json"
SEGMENTS = ROOT / "config" / "segments.yml"
_HEX = re.compile(r"^0x[0-9a-f]{8}$")
RESULTS = {"match", "mismatch", "error"}


def _attempts():
    return json.loads(ATTEMPTS.read_text())["attempts"]


def _segments():
    return yaml.safe_load(SEGMENTS.read_text())


def test_schema():
    for a in _attempts():
        assert _HEX.match(a["function"]), a
        assert len(a["source_sha256"]) == 64
        assert a["compiler_id"] and isinstance(a["cc1_flags"], list)
        assert isinstance(a["maspsx_args"], list)
        assert a["result"] in RESULTS, a
        if a["result"] == "mismatch":
            assert isinstance(a["differing_words"], int) and a["differing_words"] >= 1


def test_no_duplicate_combos():
    seen = set()
    for a in _attempts():
        key = (a["function"], a["source_sha256"],
               a.get("declaration_profile", "source"), a["compiler_id"],
               tuple(a["cc1_flags"]), tuple(a["maspsx_args"]))
        assert key not in seen, f"duplicate attempt row: {key}"
        seen.add(key)


def test_every_shipped_c_entry_has_a_match():
    seg = _segments()
    c_starts = [a["start"] for a in seg["attempted"]
                if str(a["source"]).endswith(".c")]
    by_fn = {}
    for a in _attempts():
        by_fn.setdefault(a["function"], []).append(a)
    for start in c_starts:
        va = start if isinstance(start, int) else int(start, 16)
        key = f"{va:#010x}"
        rows = by_fn.get(key, [])
        assert any(r["result"] == "match" for r in rows), \
            f"shipped C entry {key} has no recorded match in the attempts log"


def test_winning_flags_equal_pinned_c_toolchain():
    """The pinned c_toolchain must correspond to a recorded MATCH row."""
    seg = _segments()
    ct = seg["c_toolchain"]
    win = [a for a in _attempts()
           if a["result"] == "match"
           and a["compiler_id"] == ct["compiler"]
           and a["cc1_flags"] == ct["cc1_flags"]
           and a["maspsx_args"] == ct.get("maspsx_args", [])]
    assert win, ("config/segments.yml c_toolchain "
                 f"({ct['compiler']} {ct['cc1_flags']} {ct.get('maspsx_args', [])}) "
                 "has no matching 'match' row in analysis/compiler_attempts.json")

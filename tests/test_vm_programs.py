"""Guards for the mover-VM program disassembly (analysis/vm_programs.json).

CI-safe schema/invariant checks against the committed artifact. The
regenerate==committed check needs the owner's EXE and is local_media-gated.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "analysis" / "vm_programs.json").read_text())

HEXA = re.compile(r"0x[0-9a-f]+$")


def test_schema():
    assert DOC["generated_by"] == "tools/gen_vm_disasm.py"
    assert DOC["opcode_table"] == "0x8001b2f4"
    assert DOC["call_table"] == "0x8001b35c"
    assert len(DOC["call_sub_targets"]) == 9
    assert DOC["programs"], "no programs decoded"
    for pr in DOC["programs"]:
        assert HEXA.match(pr["entry"]) and HEXA.match(pr["end"])
        for ins in pr["instructions"]:
            assert HEXA.match(ins["ip"])
            assert ("op" in ins)


def test_known_facts_reproduced():
    """The disasm must keep reproducing the hand-decoded ground truth
    (src_re/enemy_ai_programs.c): op17 proximity radii per program."""
    radii = {}
    for pr in DOC["programs"]:
        for ins in pr["instructions"]:
            if ins.get("op") == "player_proximity" and ins.get("radius") is not None:
                radii[ins["ip"]] = ins["radius"]
    assert radii.get("0x80077a08") == 700, "worm radius"
    assert radii.get("0x80077a70") == 1200, "wall_worm radius"
    assert radii.get("0x800775fe") == 1200, "mosquito radius"


def test_call_table_matches_canon():
    """CALL sub-table targets documented in FUNC_8004C13C."""
    subs = set(DOC["call_sub_targets"])
    for t in ("0x80057a94", "0x80057920", "0x80057c74", "0x80057b84"):
        assert t in subs, f"resident CALL sub {t} missing"


@pytest.mark.local_media
def test_regeneration_is_identical():
    p = ROOT / "analysis" / "vm_programs.json"
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    proc = subprocess.run([sys.executable, "tools/gen_vm_disasm.py"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert hashlib.sha256(p.read_bytes()).hexdigest() == before

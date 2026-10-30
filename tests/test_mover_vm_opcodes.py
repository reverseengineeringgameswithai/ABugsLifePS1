"""Guards for the mover-VM opcode decode.

See ObsidianVault/Experiments/EXP_2026-08-04_mover_vm_indistinguishable_opcodes.md.

Eight opcodes that all dispatch to 0x8004C818 carried eight different names, every one
marked CONFIRMED. 0x8004C818 is not an operation body -- it is the interpreter's shared
loop tail. These tests protect the structural property, not just the corrected labels.
"""

import json
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "tools" / "gen_vm_disasm.py"
ART_JSON = ROOT / "analysis" / "vm_programs.json"
ART_MD = ROOT / "analysis" / "vm_programs.md"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"

OP_TABLE = 0x8001B2F4
PROG_PTRS = 0x80077AF8
REGION_LO, REGION_HI = 0x8007745C, 0x80077AF8
SHARED_TAIL = 0x8004C818
FICTIONAL = ["park_end", "park_seek", "park_arrive_test", "park_arrive_stop",
             "park_path", "park_seek18", "park19", "park21"]


def u32(va):
    b = EXE.read_bytes()
    return struct.unpack_from("<I", b, 0x800 + (va - 0x80010000))[0]


def handlers():
    return [u32(OP_TABLE + i * 4) for i in range(26)]


def test_the_eight_slots_really_do_share_one_handler():
    """The load-bearing fact. If this ever changes, the whole finding is void."""
    h = handlers()
    shared = [i for i, a in enumerate(h) if a == SHARED_TAIL]
    assert shared == [1, 6, 7, 8, 10, 18, 19, 21]


def test_exactly_one_shared_group_exists():
    """Scoping: every other opcode has its own handler, so the rest of the ISA
    decode is untouched by this correction."""
    h = handlers()
    groups = {}
    for i, a in enumerate(h):
        groups.setdefault(a, []).append(i)
    multi = {a: v for a, v in groups.items() if len(v) > 1}
    assert list(multi) == [SHARED_TAIL], multi


def test_no_fictional_park_names_remain_in_the_artifact():
    md = ART_MD.read_text()
    for name in FICTIONAL:
        assert name not in md, name


def test_the_shared_opcodes_are_labelled_indistinguishable():
    d = json.loads(ART_JSON.read_text())
    seen = False
    for prog in (d["programs"] if isinstance(d["programs"], list)
                 else d["programs"].values()):
        for ins in (prog.get("code") or prog.get("instructions") or prog):
            if isinstance(ins, dict) and ins.get("idx") in (1, 6, 7, 8, 10, 18, 19, 21):
                assert ins["op"] == "noop_shared_tail", ins
                assert ins["conf"] == "INDISTINGUISHABLE", ins
                seen = True
    assert seen, "no shared-tail opcode appeared in any decoded program"


def test_program_count_is_derived_and_is_forty_not_thirteen():
    n = 0
    while n < 256 and REGION_LO <= u32(PROG_PTRS + n * 4) < REGION_HI:
        n += 1
    assert n == 40
    d = json.loads(ART_JSON.read_text())
    progs = d["programs"]
    assert len(progs) == 40, "artifact decodes %d of %d programs" % (len(progs), n)


def test_generator_aborts_if_a_distinction_is_reintroduced():
    """The point of the fix: this error class is now structurally impossible, not
    merely corrected once."""
    src = GEN.read_text()
    bad = src.replace('    6: ("noop_shared_tail", "INDISTINGUISHABLE"),',
                      '    6: ("park_seek", "CONFIRMED"),')
    assert bad != src, "the line the guard test rewrites has moved"
    tmp = ROOT / "tools" / "_gen_vm_disasm_guardtest.py"
    tmp.write_text(bad)
    try:
        r = subprocess.run(["python3", str(tmp.relative_to(ROOT))],
                           capture_output=True, text=True, cwd=ROOT)
        assert r.returncode != 0
        assert "cannot differ" in (r.stderr + r.stdout)
    finally:
        tmp.unlink(missing_ok=True)


def test_regenerating_is_idempotent():
    before = ART_MD.read_text(), ART_JSON.read_text()
    subprocess.run(["python3", "tools/gen_vm_disasm.py"], check=True,
                   capture_output=True, cwd=ROOT)
    assert (ART_MD.read_text(), ART_JSON.read_text()) == before


def test_downstream_rows_are_flagged_not_silently_left():
    """The 6 rows citing the fictional names are FLAGGED, not re-derived -- that
    would be a campaign, not this fix. But leaving a known-fictional label
    uncaveated is the 'partial update is worse than none' trap."""
    import yaml
    doc = yaml.safe_load((ROOT / "analysis" / "mechanics_baseline.yaml").read_text())
    rows = None
    for v in doc.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            rows = {r["id"]: r for r in v}
            break
    for rid in ("D08_flies", "D09_cockroaches", "D12_centipedes_earthworms",
                "D13_armored_beetles", "D17_bird", "D19_molt"):
        b = " ".join(rows[rid]["bindings"])
        assert "MOVER-VM LABEL CAVEAT" in b, rid
        assert "has NOT been re-derived" in b, rid


def test_canon_records_the_correction():
    t = (ROOT / "ObsidianVault" / "Canon" / "Systems" / "SYS_event_vm.md").read_text()
    assert "INDISTINGUISHABLE" in t
    assert "0x8004C818" in t
    assert "40 of 40" in t

"""Gate for tools/repair_function_coverage.c.

The repaired list is a candidate replacement for the input of nineteen static
tools, so the tests that matter are the ones that catch it making things WORSE:

  * over-fragmentation -- splitting a real function loses dataflow across the
    split, which would silently degrade every provenance result. Two versions of
    this tool did exactly that, and the emitter is the canary.
  * overlaps -- a census iterating an overlapping list scans bytes twice and
    reports inflated counts.
  * regression -- an original entry disappearing or being renamed.

The coverage percentage is the least interesting assertion here and is pinned
loosely on purpose: a version that reached 100% by swallowing padding would be
worse than this one at 92.8%.
"""
from __future__ import annotations

import json
import struct
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools/repair_function_coverage.c"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
ORIG = ROOT / "analysis/functions_resident.txt"
REPAIRED = ROOT / "analysis/functions_resident_repaired.txt"

EMITTER = 0x80010000
EMITTER_END = 0x80013108          # grass_mound_mesh_builder starts here

# The hoisted-load family the any% campaign surfaced. Every one lives in code the
# original census dropped; all of them must resolve in the repaired list.
FAMILY = [0x80010BF4, 0x80010D9C, 0x800110A8, 0x8001129C, 0x800119B0, 0x80012098,
          0x8001277C, 0x80012CEC, 0x80013B84, 0x80013D58]


def load(p: Path):
    out = []
    for line in p.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        q = line.split()
        if len(q) >= 3:
            out.append((int(q[0], 16), int(q[1]), q[2]))
    return sorted(out)


def owner(fns, pc):
    for a, n, nm in fns:
        if a <= pc < a + n:
            return nm
    return None


@pytest.fixture(scope="module")
def tool(tmp_path_factory):
    out = tmp_path_factory.mktemp("rfc") / "rfc"
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", str(out), str(SRC)],
                   check=True)
    return out


@pytest.fixture(scope="module")
def fresh(tool, tmp_path_factory):
    d = tmp_path_factory.mktemp("out")
    lst, js = d / "f.txt", d / "r.json"
    r = subprocess.run([str(tool), str(EXE), str(ORIG), "--out", str(lst), "--json", str(js)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return load(lst), json.loads(js.read_text())


def test_builds_werror_clean():
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-o", str(Path(d) / "x"), str(SRC)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_rejects_a_wrong_image(tool):
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.exe"
        b = bytearray(EXE.read_bytes())
        off = 0x800 + (0x80010C88 - 0x80010000)
        b[off:off + 4] = b"\x00\x00\x00\x00"
        bad.write_bytes(bytes(b))
        r = subprocess.run([str(tool), str(bad), str(ORIG)], capture_output=True, text=True)
        assert r.returncode != 0
        assert "pin" in r.stderr.lower()


def test_committed_artifact_matches_a_fresh_run(fresh):
    fns, _ = fresh
    assert fns == load(REPAIRED), "the committed repaired list is stale; regenerate it"


def test_no_overlaps(fresh):
    """An overlapping list makes every consuming census double-count."""
    fns, _ = fresh
    for (a, n, na), (b, _m, nb) in zip(fns, fns[1:]):
        assert a + n <= b, f"{na} at 0x{a:08X} runs into {nb} at 0x{b:08X}"


def test_it_is_a_strict_superset_of_the_original(fresh):
    """Recovery may only add. An entry that vanished or got renamed would break
    every tool and doc that refers to it by name."""
    fns, _ = fresh
    orig = load(ORIG)
    by_addr = {a: nm for a, _n, nm in fns}
    for a, _n, nm in orig:
        assert a in by_addr, f"original entry 0x{a:08X} {nm} disappeared"
        assert by_addr[a] == nm, f"0x{a:08X} renamed {nm} -> {by_addr[a]}"


def test_the_emitter_is_recovered_WHOLE_not_in_pieces(fresh):
    """THE canary for over-fragmentation.

    Two earlier versions cut per_object_mesh_draw_payload_emitter into five
    pieces -- once by letting the walk boundary creep as entries were added, once
    by linear-sweeping data that decoded as `jal`. Both looked like progress on
    the coverage number while destroying the function."""
    fns, _ = fresh
    ent = [(a, n) for a, n, _ in fns if a == EMITTER]
    assert len(ent) == 1
    assert ent[0][1] == EMITTER_END - EMITTER, \
        f"emitter is {ent[0][1]} bytes, expected {EMITTER_END - EMITTER}"
    inside = [a for a, _n, _nm in fns if EMITTER < a < EMITTER_END]
    assert not inside, f"emitter body was split by entries at {[hex(x) for x in inside]}"


def test_every_campaign_pc_now_resolves(fresh):
    """The concrete thing the repair exists to fix."""
    fns, _ = fresh
    orig = load(ORIG)
    assert sum(1 for pc in FAMILY if owner(orig, pc) is None) > 0, \
        "these PCs must be uncovered in the ORIGINAL, else the test proves nothing"
    for pc in FAMILY:
        assert owner(fns, pc) is not None, f"0x{pc:08X} still unlisted after repair"


def test_recovery_moved_coverage_substantially(fresh):
    _fns, rep = fresh
    assert rep["listed_covered_percent"] < 91.0
    assert rep["repaired_covered_percent"] > 92.0
    assert rep["bytes_recovered_by_extension"] > 11000


def test_it_does_not_claim_padding(fresh):
    """Reaching 100% by swallowing unreferenced bytes would be a worse tool: a
    census that reads padding as code emits false sites."""
    _fns, rep = fresh
    assert rep["still_unclaimed_bytes"] > 0


def test_recovered_entries_are_real_code_not_data(fresh):
    """No entry may begin on a zero word.

    This is the assertion that caught the tool inventing functions. Both entries
    an earlier version 'recovered' (0x8007F204, 0x8007F2B8) were minted from words
    decoding as REGIMM bgezal -- which GCC 2.7.2 never emits -- and landed in a
    zero run inside the small-data region below $gp. One was then extended across
    8,768 bytes that are 72.4% zero, inflating coverage by two whole points."""
    fns, rep = fresh
    img = EXE.read_bytes()
    for r in rep["recovered"]:
        a = int(r["addr"], 16)
        w = struct.unpack_from("<I", img, 0x800 + a - 0x80010000)[0]
        assert w != 0, f"recovered entry {r['addr']} starts on a zero word"
        assert any(a == x for x, _n, _nm in fns)


def test_data_tables_are_refused_not_walked_as_code(fresh):
    """The census lists DATA under function names. Walking one from its "entry"
    decodes a table as instructions and wanders: contact_metadata_table_a was
    extended by 8,068 bytes of a plainly regular lookup table, and
    contact_action_dispatch by 2,016 bytes of a 0x8005Bxxx pointer table. Ten
    thousand bytes of pure inflation, on a coverage number that read 95.0%."""
    fns, rep = fresh
    by_addr = {a: n for a, n, _nm in fns}
    assert by_addr[0x80079E30] == 6156, "contact_metadata_table_a must NOT be extended"
    assert by_addr[0x8001B570] == 696, "contact_action_dispatch must NOT be extended"
    refused = rep.get("refused_extension_bytes")
    if refused is not None:
        assert refused > 8000


def test_the_two_known_bogus_entries_never_come_back(fresh):
    fns, _rep = fresh
    starts = {a for a, _n, _nm in fns}
    for bogus in (0x8007F204, 0x8007F2B8):
        assert bogus not in starts, f"0x{bogus:08X} is small data, not a function"


def test_the_audit_reports_zero_content_so_code_is_not_overstated():
    """"Reached by a branch" alone called 46,020 bytes live code; 20.5% of it is
    zero words. The dense figure is the defensible one and must be published."""
    import json as _j
    a = _j.loads((ROOT / "analysis/phase4_text_coverage_audit.json").read_text())
    assert a["dropped_code_zero_bytes"] > 0
    assert a["dropped_code_dense_bytes"] < a["dropped_code_bytes"]
    assert "overstates" in a["zero_caveat"]
    for g in a["gaps"]:
        assert "zero_percent" in g


def test_the_measured_impact_artifact_agrees_with_the_lists():
    """The impact numbers are what justify (or refuse) swapping the canonical
    file, so they must not drift from the artifacts they describe."""
    imp = json.loads((ROOT / "analysis/phase4_coverage_repair_impact.json").read_text())
    assert imp["affine_region_census"]["sites_before"] == \
        imp["affine_region_census"]["sites_after"], \
        "if the region census ever DOES move, this gate must be revisited, not edited"
    assert imp["region_provenance"]["hits_before"] == imp["region_provenance"]["hits_after"]
    assert imp["region_provenance"]["unresolved_after"] > \
        imp["region_provenance"]["unresolved_before"]
    assert imp["coverage"]["functions_after"] == len(load(REPAIRED))
    assert "Do NOT swap" in imp["recommendation"]

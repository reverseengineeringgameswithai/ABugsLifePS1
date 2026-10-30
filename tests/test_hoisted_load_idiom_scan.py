"""Gate for tools/hoisted_load_idiom_scan.c.

This scan admits 22 PCs into E16's accounted-for set, so a wrong match here
launders a real finding into a dismissal. The central test therefore DOES NOT
trust the C tool's own report: it re-decodes every hit straight from the image
with an independent implementation and checks the four-instruction idiom itself.
A second implementation has caught a 2x count inflation in this project before.
"""
from __future__ import annotations

import json
import struct
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools/hoisted_load_idiom_scan.c"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
TEXT_LO, HDR = 0x80010000, 0x800

# The two the any% campaign actually caught, four levels apart.
OBSERVED = {"0x80010bf8", "0x80010da0"}


@pytest.fixture(scope="module")
def tool(tmp_path_factory):
    out = tmp_path_factory.mktemp("hls") / "hls"
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", str(out), str(SRC)],
                   check=True)
    return out


@pytest.fixture(scope="module")
def result(tool, tmp_path_factory):
    j = tmp_path_factory.mktemp("hlsj") / "r.json"
    r = subprocess.run([str(tool), str(EXE), "--json", str(j)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(j.read_text())


@pytest.fixture(scope="module")
def img():
    return EXE.read_bytes()


def word(img, va):
    return struct.unpack_from("<I", img, HDR + va - TEXT_LO)[0]


def test_builds_werror_clean():
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-o", str(Path(d) / "x"), str(SRC)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_rejects_a_shifted_image(tool):
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.exe"
        b = bytearray(EXE.read_bytes())
        b[HDR + 0x80010BF4 - TEXT_LO:HDR + 0x80010BF4 - TEXT_LO + 4] = b"\x00\x00\x00\x00"
        bad.write_bytes(bytes(b))
        r = subprocess.run([str(tool), str(bad)], capture_output=True, text=True)
        assert r.returncode != 0
        assert "pinned" in r.stderr.lower()


def test_it_found_the_family_not_just_the_two_movies_caught(result):
    assert result["sites"] >= 22
    logged = {h["logged_pc"].lower() for h in result["hits"]}
    assert OBSERVED <= logged, "the campaign's own finds must be in the family"


def test_logged_pc_is_the_instruction_after_the_load(result):
    """accessLog reports PC+4. Getting this wrong would match every event against
    the wrong address and silently accept unrelated PCs."""
    for h in result["hits"]:
        assert int(h["logged_pc"], 16) == int(h["load_pc"], 16) + 4


def test_every_hit_really_decodes_as_the_idiom(result, img):
    """INDEPENDENT re-decode. If this disagrees with the C matcher, the C matcher
    is what gets fixed -- these 22 PCs are being excused on the strength of it."""
    for h in result["hits"]:
        cmp_pc = int(h["cmp_pc"], 16)
        w0, w1, w2, w3 = (word(img, cmp_pc + i) for i in (0, 4, 8, 12))

        # [0] slt/sltu rCond, rIdx, rLim
        assert w0 >> 26 == 0 and (w0 & 0x3F) in (0x2A, 0x2B), f"{h['cmp_pc']} not slt/sltu"
        cond, idx = (w0 >> 11) & 31, (w0 >> 21) & 31
        assert cond == h["cond_reg"] and idx == h["idx_reg"]

        # [1] add/addu rIdx, rIdx, rBase
        assert w1 >> 26 == 0 and (w1 & 0x3F) in (0x20, 0x21), "not add/addu"
        assert (w1 >> 11) & 31 == idx
        rs1, rt1 = (w1 >> 21) & 31, (w1 >> 16) & 31
        assert idx in (rs1, rt1)
        assert h["base_reg"] == (rt1 if rs1 == idx else rs1)

        # [2] load rDst, 0(rIdx) -- and it is a LOAD, which is why no hit can write
        assert (w2 >> 26) in (0x20, 0x21, 0x23, 0x24, 0x25), "not a load"
        assert (w2 >> 21) & 31 == idx
        assert (w2 & 0xFFFF) == 0

        # [3] beq/bne rCond, $zero -- the test consumed AFTER the load
        assert (w3 >> 26) in (4, 5), "not beq/bne"
        rs3, rt3 = (w3 >> 21) & 31, (w3 >> 16) & 31
        assert (rs3 == cond and rt3 == 0) or (rt3 == cond and rs3 == 0)


def test_hits_are_unique_and_ordered(result):
    pcs = [int(h["load_pc"], 16) for h in result["hits"]]
    assert pcs == sorted(pcs)
    assert len(pcs) == len(set(pcs))


def test_the_artifact_states_the_pc_off_by_one_trap(result):
    """A consumer matching watch events against load_pc would find nothing and
    conclude the family is irrelevant."""
    assert "after the access" in result["note"].lower()
    assert "logged_pc" in result["note"]

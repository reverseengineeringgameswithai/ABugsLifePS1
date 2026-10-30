"""Guard the decomp-substrate v0 scaffold (docs/SUBSTRATE.md).

CI-safe legs: the segments manifest stays well-formed and census-consistent,
and (when the cross toolchain is installed) a SYNTHETIC 3-instruction round
trip through as -> ld -> objcopy reproduces the expected encodings — no game
bytes involved. The full byte-splat build/validate needs the owner's EXE and
is local_media-gated.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from substrate_common import (assemble_at, c_toolchain_available,  # noqa: E402
                              compile_at, load_declaration_profiles, load_segments,
                              resolve_declaration_profile, toolchain_available)

CENSUS = ROOT / "analysis" / "functions.json"
EXTENT_ACK = ROOT / "config" / "phase4_extent_audit_acknowledged.yaml"


def test_segments_manifest_well_formed():
    seg = load_segments()
    acknowledged = yaml.safe_load(EXTENT_ACK.read_text())["acknowledged"]
    reviewed_decomp_splits = {
        (int(row["entry"], 16), int(row["declared_end"], 16))
        for row in acknowledged
        if row["file"] == "config/segments.yml"
        and row["verdict"] == "decomp_segment_not_a_census_extent"
    }
    assert seg["image"] == "SCUS_942.88"
    assert seg["sha1"] == "af43de22474f15664d0e17498fbd27faeb7ed111"
    assert seg["header_bytes"] == 0x800
    assert seg["load_va"] == 0x80010000
    assert seg["text_size"] == 0x72800
    starts = {int(r["start"], 16): r for r in json.loads(CENSUS.read_text())["functions"]
              if r["space"] == "resident"}
    for a in seg["attempted"]:
        assert a["start"] < a["end"], a
        # asm entries live under asm/hand_written/ (untracked, byte-derived);
        # C entries under src/main/ (committed authored reimplementations)
        assert (a["source"].startswith("asm/hand_written/") and a["source"].endswith(".s")) \
            or (a["source"].startswith("src/main/") and a["source"].endswith(".c")), a
        for part in a.get("parts", []):
            assert a["source"].endswith(".s"), a
            assert part["source"].startswith("asm/hand_written/")
            assert part["source"].endswith(".s")
            assert a["start"] < part["start"] < a["end"], part
        rec = starts.get(a["start"])
        assert rec is not None, f"attempted {a['start']:#x} is not a census function start"
        if int(rec["end"], 16) != a["end"]:
            assert (a["start"], a["end"]) in reviewed_decomp_splits, \
                f"attempted {a['start']:#x} end {a['end']:#x} != census {rec['end']}"
        if a.get("sections"):
            assert a["source"].endswith(".c"), a
            assert a["sections"]["text"] == {"start": a["start"], "end": a["end"]}
            for section in a["sections"].values():
                assert section["start"] < section["end"], section


def test_declaration_profiles_are_explicit_and_cleanroom():
    doc = load_declaration_profiles()
    assert doc["default"] == "source"
    assert {"source", "cleanroom_prototyped", "cleanroom_unprototyped",
            "external_psyq"} <= set(doc["profiles"])
    for name in ("source", "cleanroom_prototyped", "cleanroom_unprototyped"):
        profile = resolve_declaration_profile(name)
        assert profile["name"] == name
        assert profile["evidence"]["profile"] == name
    assert (ROOT / "include" / "abl" / "psyq_decl.h").is_file()


def test_c_toolchain_block_well_formed():
    ct = load_segments().get("c_toolchain")
    assert ct, "segments.yml missing c_toolchain block"
    man = json.loads((ROOT / "tools" / "toolchain_manifest.json").read_text())
    ids = {c["id"] for c in man["compilers"]}
    assert ct["compiler"] in ids, f"{ct['compiler']} not in toolchain manifest {ids}"
    assert isinstance(ct["cc1_flags"], list) and ct["cc1_flags"]
    assert isinstance(ct.get("maspsx_args", []), list)


def test_synthetic_c_roundtrip():
    """cpp -> cc1 -> maspsx -> as reproduces a known small function's bytes,
    and re-compiling is byte-stable. Skips if the era toolchain is absent."""
    seg = load_segments()
    cid = seg["c_toolchain"]["compiler"]
    if not c_toolchain_available(cid):
        pytest.skip("era C toolchain (old-gcc + maspsx) not installed")
    src = ROOT / "build" / "substrate" / "_synthetic_test.c"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("void set_two_bytes(unsigned char *p){ p[3]=12; p[7]=0x3c; }\n")
    b1 = compile_at(src, 0x80061d04, compiler_id=cid,
                    cc1_flags=seg["c_toolchain"]["cc1_flags"],
                    maspsx_args=seg["c_toolchain"].get("maspsx_args", []))
    # SetPolyGT4 shape (words, little-endian in the image):
    #   addiu v0,0xc; sb v0,3(a0); addiu v0,0x3c; jr ra; sb v0,7(a0)
    import struct
    expect = struct.pack("<5I", 0x2402000c, 0xa0820003, 0x2402003c, 0x03e00008, 0xa0820007)
    assert b1 == expect, b1.hex()
    b2 = compile_at(src, 0x80061d04, compiler_id=cid,
                    cc1_flags=seg["c_toolchain"]["cc1_flags"],
                    maspsx_args=seg["c_toolchain"].get("maspsx_args", []))
    assert b1 == b2, "C compile is not byte-stable across runs"


def test_synthetic_roundtrip():
    """as -> ld @VA -> objcopy reproduces hand-computed MIPS-I encodings."""
    if not toolchain_available():
        pytest.skip("mips64-linux-gnu cross toolchain not installed")
    src = ROOT / "build" / "substrate" / "_synthetic_test.s"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(
        ".set noreorder\n"
        ".set noat\n"
        ".text\n"
        "addiu $t2, $zero, 0xa0\n"
        "jr    $t2\n"
        "addiu $t1, $zero, 0x39\n")
    data = assemble_at(src, 0x80065EEC)
    # LE words 0x240a00a0, 0x01400008, 0x24090039 (generic MIPS-I encodings)
    assert data == bytes.fromhex("a0000a24 08004001 39000924".replace(" ", "")), data.hex()


def test_synthetic_jal_absolute():
    """jal to an absolute .equ symbol encodes the correct R_MIPS_26 target."""
    if not toolchain_available():
        pytest.skip("mips64-linux-gnu cross toolchain not installed")
    src = ROOT / "build" / "substrate" / "_synthetic_jal.s"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(
        ".set noreorder\n"
        ".equ some_engine_fn, 0x8004fa40\n"
        ".text\n"
        "jal some_engine_fn\n"
        "nop\n")
    data = assemble_at(src, 0x80010000)
    # jal 0x8004fa40 -> 0x0C000000 | ((0x8004fa40 >> 2) & 0x03FFFFFF) = 0x0c013e90
    assert data == bytes.fromhex("903e010c 00000000".replace(" ", "")), data.hex()


def test_synthetic_internal_j_rebased_to_va():
    """substrate v2 (--section-start): an internal `j` to a LOCAL label must
    resolve to __va+offset, not the 0x80010000 link default. This is the
    section-placement fix that unlocked the internal-`j`/if-else-merge class."""
    if not toolchain_available():
        pytest.skip("mips64-linux-gnu cross toolchain not installed")
    src = ROOT / "build" / "substrate" / "_synthetic_intj.s"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(
        ".set noreorder\n"
        ".text\n"
        "beq  $5, $0, end\n"
        "nop\n"
        "j    end\n"          # internal jump to a local label
        "nop\n"
        "end:\n"
        "jr   $31\n"
        "nop\n")
    import struct
    va = 0x80123450
    data = assemble_at(src, va)
    j_word = struct.unpack("<I", data[8:12])[0]        # the `j end`
    assert (j_word >> 26) == 2, f"expected a j opcode, got {j_word:#010x}"
    target = (va & 0xF0000000) | ((j_word & 0x03FFFFFF) << 2)
    assert va <= target < va + len(data), \
        f"internal j resolved to {target:#x}, outside [{va:#x}, {va+len(data):#x})"


def test_synthetic_gp_relative():
    """substrate v2 (small_data + _gp): a small global is addressed gp-relative
    (single `lw $2,off($gp)`), not absolute lui/lw. off = symbol - _gp."""
    seg = load_segments()
    cid = seg["c_toolchain"]["compiler"]
    if not c_toolchain_available(cid):
        pytest.skip("era C toolchain (old-gcc + maspsx) not installed")
    gp = seg["gp"] if isinstance(seg.get("gp"), int) else int(seg["gp"], 16)
    gaddr = gp + 0x100
    src = ROOT / "build" / "substrate" / "_synthetic_gp.c"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(f"extern int g_{gaddr:08x};\n"
                   f"int gpf(void){{ return g_{gaddr:08x} & 1; }}\n")
    data = compile_at(src, 0x80046b14, compiler_id=cid,
                      cc1_flags=seg["c_toolchain"]["cc1_flags"],
                      maspsx_args=seg["c_toolchain"].get("maspsx_args", []),
                      small_data=True, gp=gp)
    import struct
    # gp-relative form is 3 words: lw $2,0x100($gp); jr ra; andi $2,$2,1
    assert len(data) == 12, f"expected gp-relative 12 B, got {len(data)}: {data.hex()}"
    expect = struct.pack("<3I", 0x8f820100, 0x03e00008, 0x30420001)
    assert data == expect, data.hex()


def test_synthetic_split_text_rdata():
    """A compiler-emitted constant table can be linked at a rodata VA that is
    independent of the function text VA, and is returned as a separate patch."""
    seg = load_segments()
    cid = seg["c_toolchain"]["compiler"]
    if not c_toolchain_available(cid):
        pytest.skip("era C toolchain (old-gcc + maspsx) not installed")
    src = ROOT / "build" / "substrate" / "_synthetic_split.c"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("static const int values[2]={11,22}; int pick(int i){return values[i];}\n")
    layout = {
        "text": {"start": 0x80020000, "end": 0x80020100},
        "rdata": {"start": 0x80078000, "end": 0x80078008},
    }
    built = compile_at(src, layout["text"]["start"], compiler_id=cid,
                       cc1_flags=seg["c_toolchain"]["cc1_flags"],
                       maspsx_args=seg["c_toolchain"].get("maspsx_args", []),
                       section_layout=layout)
    assert isinstance(built, dict)
    assert built["text"]
    import struct
    assert built["rdata"] == struct.pack("<2I", 11, 22)


def test_auto_defsym_resolves_undefined_symbols():
    """An undefined symbol (jal target / global) auto-resolves without an
    explicit externs entry: an address-anchored name -> its VA; an unresolvable
    name -> a clear error naming it."""
    if not toolchain_available():
        pytest.skip("mips64-linux-gnu cross toolchain not installed")
    d = ROOT / "build" / "substrate"
    d.mkdir(parents=True, exist_ok=True)
    # jal sub_8004fa40 (anchor name) -> jal 0x8004fa40, no externs given
    ok = d / "_synthetic_autodefsym.s"
    ok.write_text(".set noreorder\n.text\njal sub_8004fa40\nnop\n")
    data = assemble_at(ok, 0x80010000)
    assert data == bytes.fromhex("903e010c00000000"), data.hex()
    # explicit externs still win / resolve a non-anchor name
    ok.write_text(".set noreorder\n.text\njal engine_thing\nnop\n")
    data = assemble_at(ok, 0x80010000, externs={"engine_thing": 0x8004fa40})
    assert data == bytes.fromhex("903e010c00000000"), data.hex()
    # unresolvable symbol -> error that names it
    bad = d / "_synthetic_badsym.s"
    bad.write_text(".set noreorder\n.text\njal totally_unknown_sym\nnop\n")
    with pytest.raises(RuntimeError, match="totally_unknown_sym"):
        assemble_at(bad, 0x80010000)


@pytest.mark.local_media
def test_byte_splat_build_validates():
    """Full pipeline on the owner's EXE: build then validate must PASS."""
    if not toolchain_available():
        pytest.skip("mips64-linux-gnu cross toolchain not installed")
    if not (ROOT / "REBUILD" / "files" / "SCUS_942.88").exists():
        pytest.skip("owner's EXE not on this host")
    for script in ("tools/build_psx_exe.py", "tools/validate_build.py"):
        p = subprocess.run([sys.executable, script], cwd=ROOT,
                           capture_output=True, text=True)
        assert p.returncode == 0, f"{script} failed:\n{p.stdout}\n{p.stderr}"

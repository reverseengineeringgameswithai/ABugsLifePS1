"""CI-safe tests for tools/exe_read.py xref logic, using SYNTHETIC instruction
bytes (no copyrighted EXE input). Validates gp-relative and absolute (lui+ld/st)
detection so the static xref scanner is trustworthy on the real image.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import exe_read  # noqa: E402

GP = 0x80081d98


def _build():
    # 0x800-byte header, then known instructions at known VAs.
    data = bytearray(0x900)
    def put(va, word):
        struct.pack_into("<I", data, (va - 0x80010000) + 0x800, word)
    # gp-relative to 0x800822f4 (gp-off 0x55c): sw v0 / lw v1
    put(0x80010010, 0xAF82055C)   # sw v0, 0x55c(gp)
    put(0x80010014, 0x8F83055C)   # lw v1, 0x55c(gp)
    # absolute to 0x80082504: lui t0,0x8008 ; sw t1,0x2504(t0)
    put(0x80010020, 0x3C088008)   # lui t0, 0x8008
    put(0x80010024, 0xAD092504)   # sw  t1, 0x2504(t0)
    return bytes(data)


def test_gp_relative_store_and_load():
    res = exe_read.xref(_build(), 0x800822f4, GP)
    kinds = {(va, mn) for va, k, mn, rt in res}
    assert (0x80010010, "sw") in kinds, "gp-relative store not found"
    assert (0x80010014, "lw") in kinds, "gp-relative load not found"
    writers = [r for r in res if r[2][0] == "s"]
    assert any(va == 0x80010010 for va, *_ in writers)


def test_absolute_lui_store():
    res = exe_read.xref(_build(), 0x80082504, GP)
    assert any(va == 0x80010024 and mn == "sw" and k == "abs" for va, k, mn, rt in res), \
        "absolute lui+sw not found"


def test_no_false_positive_other_addr():
    # an address with no accesses in the synthetic image
    res = exe_read.xref(_build(), 0x800a6504, GP)
    assert res == [], f"unexpected hits: {res}"


def _build_overlay():
    # A RAW overlay blob (no PS-EXE header): code starts at file offset 0,
    # runtime base 0x800b39a0 (Region-A). Two writes to the cursor 0x800822f4.
    data = bytearray(0x40)
    def put(off, word):
        struct.pack_into("<I", data, off, word)
    put(0x00, 0xAF82055C)   # sw v0, 0x55c(gp)        -> gp-relative cursor write
    put(0x10, 0x3C018008)   # lui at, 0x8008
    put(0x14, 0xAC2222F4)   # sw  v0, 0x22f4(at)      -> absolute cursor write
    return bytes(data)


def test_overlay_base_and_hdr_remap():
    BASE = 0x800B39A0
    res = exe_read.xref(_build_overlay(), 0x800822f4, GP, base=BASE, hdr=0, span=0x40)
    vas = {(va, mn, k) for va, k, mn, rt in res}
    # gp-relative store at file 0 -> overlay VA BASE+0
    assert (BASE + 0x00, "sw", "gp") in vas, f"overlay gp store not remapped: {vas}"
    # absolute lui+sw store at file 0x14 -> overlay VA BASE+0x14
    assert (BASE + 0x14, "sw", "abs") in vas, f"overlay abs store not remapped: {vas}"


def test_exe_default_base_unchanged():
    # The overlay params must default to EXE layout (regression guard).
    res = exe_read.xref(_build(), 0x800822f4, GP)
    assert any(va == 0x80010010 and mn == "sw" for va, k, mn, rt in res)


def _build_ea():
    # Three stores to 0x800822f4 via DIFFERENT idioms + one decoy to a nearby addr.
    data = bytearray(0x900)
    def put(va, word):
        struct.pack_into("<I", data, (va - 0x80010000) + 0x800, word)
    # idiom 1: lui+sw with offset (the form xref already catches)
    put(0x80010000, 0x3C018008)   # lui at,0x8008
    put(0x80010004, 0xAC2222F4)   # sw  v0,0x22f4(at)        ea=0x800822f4
    # idiom 2: lui+ori then sw,0(reg)  (xref MISSES this)
    put(0x80010010, 0x3C0A8008)   # lui t2,0x8008
    put(0x80010014, 0x354A22F4)   # ori t2,t2,0x22f4
    put(0x80010018, 0xAD420000)   # sw  v0,0(t2)             ea=0x800822f4
    # idiom 3: lui+addiu pointer then sw,4(reg) (base = counter 0x800822f0, +4)
    put(0x80010020, 0x3C0B8008)   # lui t3,0x8008
    put(0x80010024, 0x256B22F0)   # addiu t3,t3,0x22f0
    put(0x80010028, 0xAD640004)   # sw  a0,4(t3)             ea=0x800822f4
    # decoy: store to 0x800822f0 (counter) — must NOT match target 0x800822f4
    put(0x80010030, 0x3C0C8008)   # lui t4,0x8008
    put(0x80010034, 0xAD8222F0)   # sw  v0,0x22f0(t4)        ea=0x800822f0
    return bytes(data)


def test_find_addr_stores_all_idioms():
    res = exe_read.find_addr_stores(_build_ea(), 0x800822f4)
    vas = {va for va, mn, rt, eab, off in res}
    assert 0x80010004 in vas, "lui+sw(offset) store missed"
    assert 0x80010018 in vas, "lui+ori; sw,0(reg) store missed (the idiom xref cannot see)"
    assert 0x80010028 in vas, "lui+addiu ptr; sw,4(reg) store missed"
    assert 0x80010034 not in vas, "decoy store to neighbouring 0x22f0 wrongly matched"


def test_region_stats_metadata():
    # uniform 0..255 -> entropy 8.0, mean 127.5, distinct 256 (no raw bytes returned)
    data = bytearray(0x800) + bytes(range(256))
    st = exe_read.region_stats(bytes(data), 0x80010000, 0x80010100, base=0x80010000, hdr=0x800)
    assert st["size"] == 256 and st["distinct"] == 256
    assert abs(st["entropy_bits"] - 8.0) < 0.001
    assert abs(st["mean"] - 127.5) < 0.01
    assert "size" in st and not any(k.startswith("byte") for k in st), "must not leak raw bytes"
    # constant 0x80 -> entropy 0, distinct 1, mean 128.0
    data2 = bytearray(0x800) + bytes([0x80]) * 64
    st2 = exe_read.region_stats(bytes(data2), 0x80010000, 0x80010040, base=0x80010000, hdr=0x800)
    assert st2["entropy_bits"] == 0.0 and st2["distinct"] == 1 and st2["mean"] == 128.0


def test_disasm_one_known_encodings():
    cases = {
        0x27bdffe8: "addiu sp,sp,-24",
        0x8fbf0010: "lw ra,16(sp)",
        0x03e00008: "jr ra",
        0xaf82055c: "sw v0,1372(gp)",      # 0x55c = 1372
        0x3c088008: "lui t0,0x8008",
        0x0c015259: "jal 0x80054964",
        0x00000000: "nop",
        0x2c820011: "sltiu v0,a0,17",
    }
    for w, expect in cases.items():
        got = exe_read.disasm_one(0x80010000, w)
        assert got == expect, f"0x{w:08x}: got {got!r} expected {expect!r}"

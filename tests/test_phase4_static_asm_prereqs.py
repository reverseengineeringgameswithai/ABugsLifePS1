import subprocess
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]


def instruction(op, rs=0, rt=0, rd=0, shift=0, function=0, immediate=0):
    if op == 0:
        return (rs << 21) | (rt << 16) | (rd << 11) | (shift << 6) | function
    return (op << 26) | (rs << 21) | (rt << 16) | (immediate & 0xFFFF)


def build_exe(path, words):
    header = bytearray(0x800)
    header[:8] = b"PS-X EXE"
    struct.pack_into("<II", header, 0x18, 0x80010000, len(words) * 4)
    path.write_bytes(header + b"".join(struct.pack("<I", word) for word in words))


def test_c_probe_separates_typed_candidates_data_gaps_and_invalid_encodings(tmp_path):
    exe = tmp_path / "fixture.exe"
    extents = tmp_path / "extents.tsv"
    binary = tmp_path / "probe"
    words = [
        instruction(9, rs=0, rt=10, immediate=0xB0),
        instruction(0, rs=10, rd=31, function=9),
        0,
        instruction(0, rs=31, function=8),
        0,
        instruction(0, rs=3, rt=1, function=8),  # reserved rt: not a valid jr
        0,
        0,
        instruction(0, rs=0, function=8),        # valid encoding in data
        0,
        0,
        0,
        instruction(0, rs=4, rd=31, function=9), # valid encoding in a gap
        0,
        0,
        0,
    ]
    build_exe(exe, words)
    extents.write_text(
        "80010000\t80010020\tcode\tfixture_code\n"
        "80010020\t80010030\tdata\tfixture_data\n",
        encoding="ascii",
    )
    subprocess.run(
        [
            "cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
            str(ROOT / "tools/phase4_static_asm_probe.c"), "-o", str(binary),
        ],
        check=True,
    )
    output = subprocess.run(
        [str(binary), str(exe), str(extents)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout
    candidates = [line.split("\t") for line in output.splitlines() if line.startswith("candidate\t")]
    observed = {(row[1], row[2], row[5]) for row in candidates}
    assert observed == {
        ("0x80010004", "jalr", "code"),
        ("0x8001000c", "jr_return", "code"),
        ("0x80010020", "jr", "data"),
        ("0x80010030", "jalr", "unclaimed"),
    }
    summary = next(line.split("\t") for line in output.splitlines() if line.startswith("summary\t"))
    assert summary[1:6] == ["48", "16", "3", "1", "1"]


def test_ratchet_contract_forbids_f01_and_writer_census_edits():
    contract = (ROOT / "config/phase4_static_asm_ratchet_contract.md").read_text(encoding="utf-8")
    assert "Do not edit any `phase4_f01_*`" in contract
    assert "Do not rerun, widen, reinterpret, or promote the direct static writer census" in contract
    assert "item2_ready_for_review` and `strict_frontier_closed` false" in contract

"""Synthetic regressions for the chunk-31 seed read/edit/export path (M6).

These exercise the FULL editor seed pipeline — parse -> edit -> serialize ->
recompress -> splice into a LEVEL.RAW -> re-read -> verify — using only
synthetic seed tables built in-test. No copyrighted disc bytes are required, so
this runs in the default safe suite.
"""

from __future__ import annotations

import struct

import pytest

import decode_level_raw
import recompress_level_raw
import seed_table


def _build_seed_chunk(records: list[tuple[int, int, int, bytes]]) -> bytes:
    """Build a decompressed chunk-31 buffer from (x, y, z, meta16) tuples."""
    buf = bytearray(struct.pack("<I", seed_table.SEED_MARKER))
    for x, y, z, meta in records:
        assert len(meta) == seed_table.SEED_META_LEN
        buf += struct.pack("<iii", x, y, z) + meta
    return bytes(buf)


def _sample_records() -> list[tuple[int, int, int, bytes]]:
    # A mix of active records and one inactive (all-zero) slot.
    return [
        (3095, -80, 16750, bytes.fromhex("090100000264120019004b0040204040")),
        (4837, -2325, 2813, bytes.fromhex("0b030000010a38001900010012014040")),  # "stuck" sig
        (6184, 111, 17525, bytes.fromhex("0b0000000a6438001900000009074040")),
        (0, 0, 0, bytes(seed_table.SEED_META_LEN)),                                # inactive slot
    ]


def test_parse_seed_table_schema() -> None:
    chunk = _build_seed_chunk(_sample_records())
    records = seed_table.parse_seed_table(chunk)
    assert len(records) == 4
    assert seed_table.active_count(records) == 3
    assert (records[0].x, records[0].y, records[0].z) == (3095, -80, 16750)
    assert records[0].offset == seed_table.SEED_TABLE_OFFSET
    assert records[1].offset == seed_table.SEED_TABLE_OFFSET + seed_table.SEED_RECORD_STRIDE
    # runtime world coordinate = file coordinate << 5
    assert records[2].runtime_xyz == (6184 << 5, 111 << 5, 17525 << 5)
    assert records[3].is_active is False


def test_parse_rejects_non_seed_chunk() -> None:
    bogus = struct.pack("<I", 0x101) + bytes(seed_table.SEED_RECORD_STRIDE)
    with pytest.raises(ValueError, match="not a seed chunk"):
        seed_table.parse_seed_table(bogus)


def test_parse_rejects_misaligned_body() -> None:
    chunk = struct.pack("<I", seed_table.SEED_MARKER) + bytes(seed_table.SEED_RECORD_STRIDE + 3)
    with pytest.raises(ValueError, match="whole number"):
        seed_table.parse_seed_table(chunk)


def test_move_preserves_other_records_and_metadata() -> None:
    chunk = _build_seed_chunk(_sample_records())
    records = seed_table.parse_seed_table(chunk)
    moved = seed_table.move_record(records, 2, dx=-3184, dy=0, dz=0)

    # Only seed #2's X changed; metadata + every other record byte-identical.
    assert (moved[2].x, moved[2].y, moved[2].z) == (6184 - 3184, 111, 17525)
    assert moved[2].meta == records[2].meta
    for i in (0, 1, 3):
        assert moved[i] == records[i]

    out = seed_table.serialize_seed_table(chunk, moved)
    assert len(out) == len(chunk)
    # Re-parse confirms the persisted edit and untouched neighbours/metadata.
    reparsed = seed_table.parse_seed_table(out)
    assert (reparsed[2].x, reparsed[2].y, reparsed[2].z) == (3000, 111, 17525)
    assert reparsed[2].meta == records[2].meta
    assert reparsed[1] == records[1]


def test_set_record_absolute() -> None:
    chunk = _build_seed_chunk(_sample_records())
    records = seed_table.parse_seed_table(chunk)
    out = seed_table.serialize_seed_table(chunk, seed_table.set_record(records, 1, 1000, -2325, 2813))
    reparsed = seed_table.parse_seed_table(out)
    assert (reparsed[1].x, reparsed[1].y, reparsed[1].z) == (1000, -2325, 2813)
    assert reparsed[1].meta == records[1].meta  # metadata preserved


def test_seed_chunk_roundtrips_through_real_codec() -> None:
    # The seed chunk survives the project's decompressor/recompressor unchanged.
    chunk = _build_seed_chunk(_sample_records() * 4)  # 16 slots, len % 4 == 0
    encoded = recompress_level_raw.compress_chunk(chunk, header6=b"ABL-M6")
    assert bytes(decode_level_raw.decompress_chunk(encoded)) == chunk


def _synthetic_raw(seed_chunk: bytes) -> bytes:
    """Build a 3-chunk LEVEL.RAW with the seed chunk at index 1."""
    other = bytes(range(64)) * 2  # 128 bytes, len % 4 == 0
    chunks = [
        recompress_level_raw.compress_chunk(other, header6=b"\x00" * 6),
        recompress_level_raw.compress_chunk(seed_chunk, header6=b"ABL-M6"),
        recompress_level_raw.compress_chunk(other, header6=b"\x11" * 6),
    ]
    return b"".join(chunks) + struct.pack(">I", seed_table.CHUNK_TERMINATOR)


def test_read_and_splice_seed_chunk_in_level_raw() -> None:
    # Full export path on a synthetic multi-chunk image: locate -> edit -> splice
    # -> re-read, with the seed chunk at a non-default index.
    chunk = _build_seed_chunk(_sample_records() * 4)
    raw = _synthetic_raw(chunk)

    span, records = seed_table.read_seed_chunk(raw, index=1)
    assert span.index == 1 and len(records) == 16

    edited = seed_table.serialize_seed_table(
        *_edit(chunk, records, seed=2, dx=-3184, dy=0, dz=0)
    )
    patched = seed_table.splice_chunk(raw, 1, edited)

    # The other chunks are byte-untouched; only the seed chunk's span changed.
    assert seed_table.read_chunk_decompressed(patched, 0)[1] == bytes(range(64)) * 2
    assert seed_table.read_chunk_decompressed(patched, 2)[1] == bytes(range(64)) * 2
    _, reparsed = seed_table.read_seed_chunk(patched, index=1)
    assert (reparsed[2].x, reparsed[2].y, reparsed[2].z) == (3000, 111, 17525)
    assert reparsed[2].meta == records[2].meta


def _edit(chunk: bytes, records, seed: int, dx: int, dy: int, dz: int):
    return chunk, seed_table.move_record(records, seed, dx, dy, dz)


def test_apply_seed_edits_spec_runner() -> None:
    # The declarative runner applies a move spec to a synthetic LEVEL.RAW image.
    import apply_seed_edits

    chunk = _build_seed_chunk(_sample_records() * 4)
    raw = _synthetic_raw(chunk)
    _, records = seed_table.read_seed_chunk(raw, index=1)

    new_records, edits = apply_seed_edits.apply_operations(
        records,
        [
            {"op": "move", "seed": 2, "dx": -3184, "dy": 0, "dz": 0},
            {"op": "set", "seed": 1, "x": 1000, "y": -2325, "z": 2813},
        ],
    )
    assert len(edits) == 2
    assert edits[0].new_xyz == (3000, 111, 17525)
    assert edits[1].new_xyz == (1000, -2325, 2813)

    decompressed = seed_table.read_chunk_decompressed(raw, 1)[1]
    patched = seed_table.splice_chunk(
        raw, 1, seed_table.serialize_seed_table(decompressed, new_records)
    )
    _, reparsed = seed_table.read_seed_chunk(patched, index=1)
    assert (reparsed[2].x, reparsed[2].y, reparsed[2].z) == (3000, 111, 17525)
    assert (reparsed[1].x, reparsed[1].y, reparsed[1].z) == (1000, -2325, 2813)


def test_apply_seed_edits_rejects_zero_delta() -> None:
    import apply_seed_edits

    chunk = _build_seed_chunk(_sample_records())
    records = seed_table.parse_seed_table(chunk)
    with pytest.raises(SystemExit, match="zero dx/dy/dz"):
        apply_seed_edits.apply_operations(records, [{"op": "move", "seed": 0, "dx": 0, "dy": 0, "dz": 0}])


def test_apply_seed_edits_rejects_void_coords() -> None:
    import apply_seed_edits

    chunk = _build_seed_chunk(_sample_records())
    records = seed_table.parse_seed_table(chunk)
    with pytest.raises(SystemExit, match="file-coordinate guard"):
        apply_seed_edits.apply_operations(
            records, [{"op": "set", "seed": 0, "x": 1 << 24, "y": 0, "z": 0}]
        )

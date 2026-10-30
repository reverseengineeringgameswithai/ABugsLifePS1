"""Safe LEVEL.RAW codec regressions using only policy-approved or synthetic data."""

from pathlib import Path

import decode_level_raw
import recompress_level_raw


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def test_tracked_codec_oracle_is_byte_exact() -> None:
    compressed = (TOOLS / "raw_chunk0_compressed.bin").read_bytes()
    expected = (TOOLS / "raw_chunk0_decompressed.bin").read_bytes()

    assert bytes(decode_level_raw.decompress_chunk(compressed)) == expected


def test_synthetic_codec_roundtrip_is_deterministic() -> None:
    source = bytes(range(256)) * 2

    first = recompress_level_raw.compress_chunk(source, header6=b"ABL-M2")
    second = recompress_level_raw.compress_chunk(source, header6=b"ABL-M2")

    assert first == second
    assert bytes(decode_level_raw.decompress_chunk(first)) == source


def test_synthetic_edits_roundtrip() -> None:
    source = bytearray(bytes(range(64)) * 4)
    source[40:48] = b"TESTDATA"

    encoded = recompress_level_raw.compress_chunk(bytes(source))

    assert bytes(decode_level_raw.decompress_chunk(encoded)) == source

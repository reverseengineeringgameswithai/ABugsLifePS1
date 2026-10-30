"""Guard the source-media provenance manifest (RE-basics baseline).

CI-safe, same policy as test_fixtures_manifest.py: the committed manifest
(tools/disc_provenance.json) must stay well-formed and internally consistent;
hashing of the owner's media is ADVISORY — a file absent on this host is
skipped, never failed; a file present with a different hash is provenance
drift and fails. The 700 MB disc image gets a size check only (full hashes
are verified by `tools/re_baseline.py --provenance`); the small .cue and
boot EXE are fully hashed when present.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools" / "disc_provenance.json"
REDUMP = ROOT / "tools" / "redump_expected.json"

DISC = "Disney-Pixar A Bug's Life (v1.0).bin"
CUE = "Disney-Pixar A Bug's Life (v1.0).cue"
EXE = "SCUS_942.88"


def _man():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _redump():
    return json.loads(REDUMP.read_text(encoding="utf-8"))


def test_manifest_well_formed():
    man = _man()
    assert man["release"]["serial"] == "SCUS-94288"
    assert man["release"]["version"] == "V1.0"
    assert "redump-verified" in man["provenance_policy"]
    for name in (DISC, CUE, EXE):
        assert name in man["files"], f"manifest missing {name}"
        assert "sha1" in man["files"][name]
    for rec in man["files"].values():
        for algo in ("sha1", "md5", "crc32"):
            if algo in rec:
                assert isinstance(rec[algo], str) and rec[algo] == rec[algo].lower()


def test_disc_size_matches_when_present():
    path = ROOT / DISC
    if not path.exists():
        pytest.skip("owner's disc image not on this host")
    rec = _man()["files"][DISC]
    assert path.stat().st_size == rec["size"]
    assert rec["size"] == rec["sectors"] * 2352


def test_redump_expected_well_formed():
    """The Redump reference must be well-formed and carry its datfile provenance."""
    exp = _redump()
    assert exp["source"]["url"].startswith("http://redump.org/datfile/")
    assert exp["source"]["retrieved"]
    assert exp["game"]["name"] == "Disney-Pixar A Bug's Life (USA)"
    exts = sorted(r["name"].rsplit(".", 1)[1] for r in exp["game"]["roms"])
    assert exts == ["bin", "cue"]
    for rom in exp["game"]["roms"]:
        for algo in ("crc32", "md5", "sha1"):
            assert rom[algo] == rom[algo].lower()
        assert isinstance(rom["size"], int)


def test_redump_bin_matches_manifest():
    """Formal Redump comparison (CI-safe leg): manifest identity == datfile entry.

    Chain of custody: the file==manifest leg is checked by the hashing tests /
    re_baseline --provenance; this manifest==Redump leg needs no media.
    """
    man_bin = _man()["files"][DISC]
    rd_bin = next(r for r in _redump()["game"]["roms"] if r["name"].endswith(".bin"))
    for key in ("size", "crc32", "md5", "sha1"):
        assert man_bin[key] == rd_bin[key], f"Redump mismatch on bin {key}"


def test_redump_cue_layout_matches_when_present():
    """Owner's cue must equal Redump's cue after normalizing the .bin filename."""
    path = ROOT / CUE
    if not path.exists():
        pytest.skip("owner's cue not on this host")
    exp = _redump()
    roms = {r["name"].rsplit(".", 1)[1]: r for r in exp["game"]["roms"]}
    norm = path.read_bytes().replace(DISC.encode(), roms["bin"]["name"].encode())
    assert hashlib.sha1(norm).hexdigest() == roms["cue"]["sha1"], \
        "cue differs from Redump beyond the embedded .bin filename"


@pytest.mark.parametrize("name", [CUE, EXE])
def test_small_file_sha1_when_present(name):
    path = ROOT / name
    if not path.exists():
        pytest.skip(f"{name} not on this host")
    rec = _man()["files"][name]
    h = hashlib.sha1()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    assert h.hexdigest() == rec["sha1"], f"provenance drift on {name}"
    if "size" in rec:
        assert path.stat().st_size == rec["size"]

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import confirmed_sites  # noqa: E402


def test_confirmed_sites_validate_and_cover_phase02_promotions():
    doc = yaml.safe_load((ROOT / "config/confirmed_sites.yaml").read_text())
    assert confirmed_sites.validate(doc) == []
    addresses = {entry["address"] for entry in doc["entries"]}
    assert addresses == {
        0x8004719C, 0x800471A8, 0x800471B4, 0x800471C8,
        0x8004B2CC, 0x8004D270, 0x8004D43C, 0x80052B40, 0x80055008, 0x80058DF0,
        0x80058E14, 0x8008A1F8,
    }


def test_thud_retirement_writes_are_promoted_as_interior_sites():
    doc = yaml.safe_load((ROOT / "config/confirmed_sites.yaml").read_text())
    by_id = {row["id"]: row for row in doc["entries"]}
    assert by_id["original.thud_active_bit_retire_site"]["address"] == 0x8004D270
    assert by_id["original.thud_live_table_retire_site"]["address"] == 0x8004D43C
    for key in ("original.thud_active_bit_retire_site",
                "original.thud_live_table_retire_site"):
        row = by_id[key]
        assert row["kind"] == "code_site"
        assert row["lifecycle"] == "boss_retirement"
        assert "not a callable ABI" in row["mod_contract"]


def test_interior_code_sites_are_not_function_symbols():
    symbols = {int(line.split()[0], 16) for line in
               (ROOT / "symbols/re_symbols.sym").read_text().splitlines()
               if len(line.split()) >= 2}
    doc = yaml.safe_load((ROOT / "config/confirmed_sites.yaml").read_text())
    for entry in doc["entries"]:
        if entry["kind"] == "code_site":
            assert entry["address"] not in symbols

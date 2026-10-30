"""Phase-4 E08: per-level object census gates.

Covers analysis/phase4_e08_object_census.json -- every placement table in every
LEVEL*.DAT, walked as the retail parser does with per-file base derivation.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_e08_object_census.json"


def _art():
    return json.loads(ART.read_text())


def test_c_walker_compiles():
    subprocess.run(["cc", "-O2", "-Werror", "-fsyntax-only",
                    str(ROOT / "tools/phase4_e08_object_census.c")], check=True)


def test_every_dat_parses_and_all_crosschecks_pass():
    d = _art()
    assert d["failed"] == []
    assert len(d["levels"]) == 21
    for name, val in d["crosschecks"].items():
        assert val is True, name


def test_no_unknown_contact_object_kinds_campaign_wide():
    """Every type-0x3F kind in every level is already a named identity -- the
    contact-object kind domain is closed for placement data."""
    d = _art()
    assert d["unknown_kinds"] == []
    assert set(d["campaign_kind_histogram"]) <= set(d["kind_names"])


def test_flik_letter_sets_are_balanced():
    """F/L/I/K appear in equal numbers campaign-wide: complete sets, never a
    partial one."""
    h = _art()["campaign_kind_histogram"]
    counts = [h[f"0x{k:02x}"] for k in range(0x10, 0x14)]
    assert len(set(counts)) == 1, counts
    assert counts[0] == 18


def test_every_pass1_payload_is_distinct_and_non_null():
    """LEVEL01's 'every payload content-unique' generalises to the campaign:
    9,097 records, 9,097 distinct payload pointers, zero nulls."""
    L = _art()["levels"]
    recs = sum(v["pass1_records"] for v in L.values())
    distinct = sum(v["pass1_distinct_payloads"] for v in L.values())
    nulls = sum(v["pass1_null_payload"] for v in L.values())
    assert recs == distinct == 9097
    assert nulls == 0


def test_pass1_flag_bit5_is_never_used_in_retail_data():
    """dat_reloc documents a conditional relocation field gated by flags & 0x20.
    No retail record sets it -- that parser path is dead in shipped data."""
    L = _art()["levels"]
    assert sum(v["pass1_flag_bit5"] for v in L.values()) == 0
    # while bit3 (payload-path selector) is heavily used in both tables
    assert sum(v["pass1_flag_bit3"] for v in L.values()) > 4000
    assert sum(v["pass3_flag_bit3"] for v in L.values()) > 800


def test_pass2_is_rare_and_matches_e11_on_bug_bar():
    """Pass-2 (mesh/scale registration) is non-empty in only a few files, and
    the Bug Bar DAT reproduces E11's committed 'exactly ten non-null slots'."""
    d = _art()
    assert len(d["pass2_nonempty_files"]) == 6
    bb = d["levels"]["LEVEL04/LEVEL1.DAT"]
    assert bb["pass2_entries"] == 10 and bb["pass2_nonnull"] == 10


def test_grain_and_telescope_totals_are_reported():
    h = _art()["campaign_kind_histogram"]
    assert h["0x14"] == 774          # grain placements campaign-wide
    assert h["0x30"] == 29           # telescopes / hint gems
    assert h["0x31"] == 39           # animated construct, still semantically open

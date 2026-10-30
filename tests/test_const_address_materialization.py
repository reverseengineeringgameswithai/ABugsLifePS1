"""Gate the scoped encoding census in const_address_materialization.c."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools/const_address_materialization.c"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"

E16_RANGES = ["--range", "0x8009B5A8", "0x8009B648",
              "--range", "0x8009C210", "0x8009C230",
              "--range", "0x800A65B0", "0x800A65D0"]

# The PCs E16's campaign validator already enumerates. accessLog reports the
# instruction AFTER the access, so a materialisation site at PC matches an
# enumerated entry at PC or PC+4.
ENUMERATED = {0x8003BF4C, 0x8003B9D0, 0x8003BC58, 0x8003A3BC, 0x8003A3C0,
              0x8005F6A4, 0x8003C924, 0x8003C3C4, 0x8003C5F0}


@pytest.fixture(scope="module")
def tool(tmp_path_factory):
    out = tmp_path_factory.mktemp("cam") / "cam"
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", str(out), str(SRC)],
                   check=True)
    return out


def run(tool, tmp, *args):
    j = Path(tmp) / "r.json"
    r = subprocess.run([str(tool), str(EXE), *args, "--json", str(j)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(j.read_text())


@pytest.fixture(scope="module")
def e16(tool, tmp_path_factory):
    return run(tool, tmp_path_factory.mktemp("e16"), *E16_RANGES, "--slack", "512")


def test_builds_werror_clean():
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-o", str(Path(d) / "x"), str(SRC)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_rejects_a_wrong_image(tool):
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.exe"
        bad.write_bytes(b"NOT-AN-EXE" + bytes(4096))
        r = subprocess.run([str(tool), str(bad), *E16_RANGES],
                           capture_output=True, text=True)
        assert r.returncode != 0


def test_requires_a_range(tool):
    r = subprocess.run([str(tool), str(EXE)], capture_output=True, text=True)
    assert r.returncode != 0


def test_positive_control_a_hot_range_yields_many_sites(tool, tmp_path_factory):
    """THE test that makes 'only 5' mean anything.

    Player state at 0x800A6500 is touched all over the executable. If the scanner
    finds a similarly tiny number there, it is broken, not selective."""
    hot = run(tool, tmp_path_factory.mktemp("hot"),
              "--range", "0x800A6500", "0x800A6600", "--slack", "0")
    assert hot["sites_inside"] > 50, \
        f"scanner found only {hot['sites_inside']} sites in a hot range -- it is not working"


def test_e16_windows_have_only_a_handful_of_materialisation_sites(e16):
    assert e16["sites_inside"] == 5
    assert e16["bare_address_takes"] == 2
    assert e16["direct_accesses"] == 3


def test_every_reported_e16_materialisation_site_is_already_enumerated(e16):
    """A new scanner hit is a finding, without treating missing hits as closure.

    An ADDR_TAKE is accounted for by its CONSUMER, not by its own PC -- the pair
    `lui/addiu` that builds 0x800A65B0 sits 0x20 bytes before the store that uses
    it. Asserting identity here failed, correctly, and the fix was to make the
    tool report the consumer rather than to loosen the test."""
    for s in e16["sites"]:
        if s["kind"] == "NEAR":
            continue
        if s["kind"] == "ADDR_TAKE":
            assert s["consumer_pc"], f"address-take {s['pc']} has no in-block consumer"
            pc = int(s["consumer_pc"], 16)
        else:
            pc = int(s["pc"], 16)
        assert pc in ENUMERATED or pc + 4 in ENUMERATED, \
            f"unenumerated materialisation site {s['pc']} -> {s['address']}"


def test_address_take_consumers_land_in_the_range_they_materialised(e16):
    """A consumer whose EA drifted out of the range would mean the pointer was
    built for something else and the accounting above is meaningless."""
    lo_hi = [(int(r["lo"], 16), int(r["hi"], 16)) for r in e16["ranges"]]
    for s in e16["sites"]:
        if s["kind"] != "ADDR_TAKE":
            continue
        ea = int(s["consumer_ea"], 16)
        lo, hi = lo_hi[s["range"]]
        assert lo <= ea < hi, f"{s['pc']} consumer EA {s['consumer_ea']} outside its range"


def test_near_misses_exist_and_are_outside_the_ranges(e16):
    """Near misses are the overrun suspects; they must be genuinely outside."""
    assert e16["near_misses"] > 0
    lo_hi = [(int(r["lo"], 16), int(r["hi"], 16)) for r in e16["ranges"]]
    for s in e16["sites"]:
        if s["kind"] != "NEAR":
            continue
        a = int(s["address"], 16)
        assert not any(lo <= a < hi for lo, hi in lo_hi)


def test_slack_zero_removes_near_misses(tool, tmp_path_factory):
    tight = run(tool, tmp_path_factory.mktemp("tight"), *E16_RANGES, "--slack", "0")
    assert tight["near_misses"] == 0
    assert tight["sites_inside"] == 5, "the in-range answer must not depend on slack"


def test_scope_and_claim_are_recorded_in_the_artifact(e16):
    """The honesty fields are load-bearing: the claim is only as good as its
    stated limits, and a consumer reading the JSON must see them."""
    assert "not a complete pointer-birth or access census" in e16["claim"]
    assert "46 KB" in e16["scope"] or "function census" in e16["scope"]
    assert "not chased" in e16["scope"]
    assert "could not be reached deliberately" in e16["correction_history"]


def test_canon_does_not_restore_materialisation_closure_claims():
    pages = [
        ROOT / "ObsidianVault/Canon/Memory/MEM_800A6450_registered_chunk_table_0x58_0x5F.md",
        ROOT / "ObsidianVault/Canon/Memory/MEM_8009C170_registered_chunk_table_0x28_0x2F.md",
        ROOT / "ObsidianVault/Canon/Memory/MEM_8009B4E8_registered_chunk_table_0x30_0x57.md",
    ]
    for page in pages:
        text = page.read_text()
        assert "## Reader/writer set — now PROVEN COMPLETE" not in text
        assert "So nothing outside the recorded set can deliberately form a pointer here." not in text
        assert "not a complete access census" in text
    system = (ROOT / "ObsidianVault/Canon/Systems/SYS_registered_chunk_image_resources.md").read_text()
    assert "complete for deliberate access" not in system
    assert "no materialisation site ⇒ anything reaching that address is INCIDENTAL" not in system
    assert "not a complete access census" in system


def test_scanner_source_does_not_claim_a_sound_superset():
    source = SRC.read_text()
    assert "extra candidate sites, never a missed one" not in source
    assert "no materialisation site  =>  any access that lands there is INCIDENTAL" not in source
    assert "not an access closure" in source

"""Phase-3 WP5/WP6 guards: typed records must not erase unknowns, and pool
occupancy must be measured with the GAME's predicates, not 'has bytes'."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase3_record_types as prt  # noqa: E402

TYPES = json.loads((ROOT / "analysis" / "phase3_record_types.json").read_text())
PROBE = json.loads((ROOT / "analysis" / "phase3_record_probe.json").read_text())
CFG = yaml.safe_load((ROOT / "config" / "record_types.yaml").read_text())


def test_layouts_validate():
    for rec in CFG["records"]:
        prt.validate(rec)          # raises on overlap/misalignment/extent/vocab


def test_every_byte_is_accounted_for():
    """The gate's 'without erasing unknown fields' clause, mechanised: known
    bytes + explicit unknown spans must equal the record's full extent."""
    for rec in CFG["records"]:
        acct = prt.accounting(rec)
        spans = sum(s["length"] for s in acct["unknown_spans"])
        assert acct["known_bytes"] + spans == rec["size"], rec["id"]
        assert acct["unknown_bytes"] == spans, rec["id"]
        # and the committed artifact must agree with a fresh computation
        assert TYPES["records"][rec["id"]]["known_bytes"] == acct["known_bytes"]


def test_lifetime_is_required_of_every_record():
    for rec in CFG["records"]:
        assert rec.get("lifetime", "").strip(), rec["id"]
        assert TYPES["records"][rec["id"]]["lifetime"]


def test_occupancy_uses_the_games_predicates_not_residue():
    """A dead slot keeps RESIDUE, so 'has non-zero bytes' is not occupancy.
    Guard the distinction that produced a false 64/64 capacity reading."""
    pool = PROBE["records"]["contact_record"]
    assert pool["live_predicate"] == "lifetime_ttl > 0 and (flags & 0x02)"
    assert pool["alloc_occupied_predicate"] == "(flags & 0x80) and lifetime_ttl != 0"
    o = pool["occupancy"]
    assert o["live_max"] <= o["alloc_occupied_max"] <= o["capacity"]


def test_pristine_never_approaches_the_contact_capacity_hang():
    """WP6: the allocator has no full-array escape, so all-64-occupied hangs.
    Pristine play must therefore keep real headroom — if this ever reads 0,
    the hang is reachable in the retail game and that is a finding, not a nit."""
    o = PROBE["records"]["contact_record"]["occupancy"]
    assert o["headroom_at_peak"] >= 1
    assert o["alloc_occupied_max"] < o["capacity"]


def test_unknown_bytes_are_triaged_not_hidden():
    for rid, r in PROBE["records"].items():
        t = r["unknown_byte_triage"]
        assert set(t) == {"always_zero", "constant_nonzero", "varying"}
        # every unknown byte lands in exactly one bucket
        total = sum(b["count"] for b in t.values())
        acct = TYPES["records"][rid]
        if total:                       # records with live instances observed
            assert total <= acct["unknown_bytes"]


def test_velocity_fields_and_ttl_are_typed():
    """The WP5 drain: the velocity triples and the contact TTL are proven fields
    now, not unknown bytes. Guards the corrections too — +0x30 is velocity_y (it
    was mislabelled 'knockback_velocity'), and +0x22 is a TTL, not a type."""
    recs = {r["id"]: r for r in CFG["records"]}
    player = {f["name"]: f for f in recs["player_block"]["fields"]}
    assert player["velocity_x"]["offset"] == 0x2C
    assert player["velocity_y"]["offset"] == 0x30      # was 'knockback_velocity'
    assert player["velocity_z"]["offset"] == 0x34
    assert "knockback_velocity" not in player
    contact = {f["name"]: f for f in recs["contact_record"]["fields"]}
    assert contact["velocity_y"]["offset"] == 0x10
    assert contact["gravity_per_tick"]["offset"] == 0x18
    assert contact["lifetime_ttl"]["offset"] == 0x22   # was 'active_type'
    assert "active_type" not in contact


@pytest.mark.local_media
def test_offline_pass_is_a_fresh_regeneration():
    before = json.loads((ROOT / "analysis" / "phase3_record_types.json").read_text())
    proc = subprocess.run([sys.executable, "tools/phase3_record_types.py"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    after = json.loads((ROOT / "analysis" / "phase3_record_types.json").read_text())
    before.pop("generated"), after.pop("generated")
    assert before == after

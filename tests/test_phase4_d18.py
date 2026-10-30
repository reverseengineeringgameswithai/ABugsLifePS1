"""Phase-4 D18/F09 (Thud VM FSM): machine-checkable gates."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_d18_thud_vm_fsm.json"


def _art():
    return json.loads(ART.read_text())


def test_offline_sections_regenerate_from_committed_sources():
    r = subprocess.run([sys.executable, str(ROOT / "tools/phase4_d18_thud_vm_fsm.py"),
                        "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_row_address_is_not_a_program_entry():
    e07 = json.loads((ROOT / "analysis/phase4_e07_static.json").read_text())
    s = json.dumps(e07)
    # the 40-entry program pointer table is committed; 0x800777a6 must not be in it
    tbl = json.loads(s[s.index('"entries": ["0x8007745c'):].split("]", 1)[0]
                     .replace('"entries": ', "") + "]")
    assert "0x800777a6" not in [e.lower() for e in tbl]
    assert "0x80077798" in [e.lower() for e in tbl]
    thud = json.loads((ROOT / "analysis/phase3_thud.json").read_text())
    assert thud["boss_identity"]["mover_vm_ip_at_0x70"].lower() == "0x800777a6"


def test_fight_replay_ip_parked_through_hit_and_death():
    d = _art()["FIGHT_REPLAY_POLL_ONLY_2026-08-03"]
    # the IP invariant: parked for the whole fight, including hit + death
    assert set(d["ip_histogram"]) <= {"0x800777a4", "0x800777a6"}
    assert sum(d["ip_histogram"].values()) >= 100
    # HP is NOT invariant: transient -2 hit latch (restored) + terminal zero
    assert d["hp_range"] == [0, 48, 50]
    frames = [e["relframe"] for e in d["hit_and_defeat_events"]]
    assert frames == sorted(frames) and len(frames) == 2


def test_program_semantics_pokes_are_internally_consistent():
    d = _art()["LIVE_PROGRAM_POKES_2026-08-03"]["results"]
    assert d["p19_parked_idle"]["moved"] == [0, 0, 0]
    assert d["p20_stationary_two_clip_cycle"]["moved"] == [0, 0, 0]
    assert d["p21_gated_wander"]["moved"] == [0, 0, 0]
    assert d["p22_wander"]["moved"] != [0, 0, 0]
    assert d["p23_authored_path_patrol"]["moved"] != [0, 0, 0]
    # poked IPs rest inside their own program's range
    for k, (lo, hi) in {"p19_parked_idle": (0x80077798, 0x800777AC),
                        "p20_stationary_two_clip_cycle": (0x800777AC, 0x800777D4),
                        "p21_gated_wander": (0x800777D4, 0x800777F8),
                        "p22_wander": (0x800777F8, 0x80077814),
                        "p23_authored_path_patrol": (0x80077814, 0x8007782C)}.items():
        assert lo <= int(d[k]["ip_after"], 16) < hi, k


def test_census_usage_join_shows_shared_bank():
    usage = _art()["census_program_usage"]
    ids = {u["actor_id"] for rows in usage.values() for u in rows}
    assert 36 not in ids            # Thud himself absent (bug-bar anchor is post-retire)
    assert len(ids) >= 4            # multiple species share the bank

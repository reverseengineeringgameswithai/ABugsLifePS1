"""Phase-3 guard: the sfx_dispatch (0x80050994) interface contract.

The trap this guard exists to prevent: `v0` reads 0x4 both when a sound plays and
when nothing happens, so "it returned 4, so it worked" is the wrong inference. The
SPU is the only observable that tells the truth."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "analysis" / "phase3_sfx_interface.json").read_text())


def test_function_identity_and_provenance():
    assert S["function"]["address"] == "0x80050994"
    assert S["function"]["name"] == "sfx_dispatch"
    assert S["fixture_sha256"], "no fixture pins (DoF #1)"


def test_the_seed_impact_id_really_plays():
    """a0 = -4 is what the carried-seed and dropped-seed arms pass. If this stops
    playing, either the arm attribution or the ABI is wrong."""
    assert -4 in S["ids_that_play"]
    assert S["results"]["-4"]["plays"] is True
    assert S["results"]["-4"]["voices_keyed_on"] >= 1


def test_a_real_id_space_exists():
    assert S["ids_that_play_count"] >= 20
    # every playing id started a DISTINCT sample in this range: no aliases
    assert S["distinct_sounds"] == S["ids_that_play_count"]


def test_v0_is_not_a_success_flag():
    """The whole point of the contract. Assert the trap empirically: the same v0
    appears on both outcomes, so a mod must not branch on it."""
    play = {r["v0"] for k, r in S["results"].items() if r.get("plays")}
    quiet = {r["v0"] for k, r in S["results"].items()
             if "v0" in r and not r.get("plays")}
    assert play & quiet, "v0 now separates the outcomes — the contract must change"
    assert "NOT a success flag" in S["function"]["abi"]

"""The movie validator: the operator never has to watch for anything.

Asking someone to check for a store while they play is the wrong design -- they
cannot act on it mid-recording. These gates pin that the validator makes the call
itself, that it distinguishes UNUSABLE from INCONCLUSIVE from CLEAN, and that it
was proven against a known-good movie before any real recordings arrive.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_e16_movie_validation.json"
SRC = ROOT / "tools/phase4_e16_validate_movies.py"


def _a():
    return json.loads(ART.read_text())


def test_it_was_proven_against_a_known_good_movie_first():
    """A validator nobody has run on a movie with a known answer is a guess."""
    a = _a()
    ref = [m for m in a["movies"] if "E02_FreshLoad_Clover" in m["movie"]]
    assert len(ref) == 1
    r = ref[0]
    assert r["verdict"].startswith("USABLE AND CLEAN")
    assert r["check_occupancy"] and r["check_control"] and r["check_falsifier_clean"]
    assert r["events"] > 200 and r["truncated"] is False


def test_the_positive_control_is_a_hard_check_not_a_note():
    """The failure that cost a full run earlier: reading "no writes" as a clean
    result when the instrument never engaged. A movie without a loader clear is
    INCONCLUSIVE, never clean."""
    src = SRC.read_text()
    assert "check_control" in src
    assert "cannot be shown to have engaged" in src
    assert "INCONCLUSIVE" in src
    a = _a()
    assert "control" in a["checks"]
    assert "proves the watch engaged" in a["checks"]["control"]


def test_an_unenumerated_pc_is_reported_as_a_FIND_not_a_failure():
    """The whole point of the campaign. A PC outside the enumerated set is the
    thing being looked for, so the movie stays usable and the PC is surfaced."""
    src = SRC.read_text()
    assert "USABLE AND IT FOUND SOMETHING" in src
    assert "a find, not a failure" in _a()["checks"]["falsifier"]


def test_the_enumerated_set_matches_the_proven_run():
    """Every PC observed in the boot -> frontend -> Clover run, plus the BIOS
    memset. If the set drifts from that artifact the validator is measuring
    something else."""
    enum = set(_a()["enumerated_pcs"])
    proven = json.loads((ROOT / "analysis/phase4_e16_table_read_watch.json").read_text())
    seen = set()
    for v in proven["per_table"].values():
        seen |= set(v["write_pcs"]) | set(v["read_pcs"])
    assert seen <= enum, seen - enum
    assert "0xbfc0d868" in enum          # BIOS memset, seen during boot


def test_occupancy_threshold_admits_both_recording_styles():
    """From a hub save state the tables start populated; from boot they climb.
    The check is on the PEAK so it works for either."""
    src = SRC.read_text()
    assert "occupancy_peak" in src
    assert ">= 30 populated slots" in _a()["checks"]["occupancy"]
    ref = [m for m in _a()["movies"] if "E02_FreshLoad_Clover" in m["movie"]][0]
    assert ref["occupancy_at_start"] == 0        # from-boot: starts empty
    assert ref["occupancy_peak"] >= 30           # and populates

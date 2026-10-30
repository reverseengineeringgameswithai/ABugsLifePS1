"""Guards for the E14 bounded-exhaustion evidence."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_e14_bounded_exhaustion.json"
TOOL = ROOT / "tools" / "phase4_e14_static.c"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
MEMORY = ROOT / "REBUILD" / "files" / "BITS" / "MEMORY.BIN"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_e14_disposition_is_bounded_not_solved():
    artifact = load_artifact()
    assert artifact["status"] == "substantiated_partial"
    assert artifact["disposition"] == "bounded_exhausted_move_on"
    assert artifact["additional_interpreter_movie_required"] is False


def test_table_frontier_and_corrections_are_banked():
    frontier = load_artifact()["table_static_frontier"]
    assert frontier["resident_accesses"] == 32
    assert frontier["resident_loads"] == 20
    assert frontier["resident_stores"] == 12
    assert frontier["overlay_accesses"] == 0
    assert "0x8004B4F4" in frontier["correction"]
    assert "lazy berry-column inheritance" in frontier["correction"]


def test_adaptive_law_has_both_directions_and_chase_binding():
    law = load_artifact()["adaptive_encounter_law"]
    assert "add 2" in law["positive_direction"]
    assert "subtract 2" in law["negative_direction"]
    assert "CHASE" in law["chase_binding"]
    assert "id 15" in law["grasshopper_boundary"]


def test_options_boundary_rejects_the_remap_assumption():
    options = load_artifact()["options_static_frontier"]
    assert "pad_rumble_update" in options["rumble"]
    assert "0x800822CC/0x800822D0" in options["screen_position"]
    assert "zero direct accesses" in options["audio"]
    assert "No retail control-remapping mechanism" in options["control_remap_verdict"]


def test_persistent_c_verifier(tmp_path):
    binary = tmp_path / "phase4_e14_static"
    subprocess.run(
        [
            "cc",
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-o",
            str(binary),
            str(TOOL),
        ],
        check=True,
        cwd=ROOT,
    )
    overlays = sorted(
        path
        for path in (ROOT / "REBUILD" / "files").rglob("*.BIN")
        if path != MEMORY
    )
    result = subprocess.run(
        [str(binary), str(EXE), str(MEMORY), *map(str, overlays)],
        check=True,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert "E14_STATIC PASS" in result.stdout
    assert "table_accesses=32" in result.stdout
    assert "overlay_refs=0" in result.stdout


def test_obsidian_and_canon_are_linked():
    note = (
        ROOT
        / "ObsidianVault"
        / "Experiments"
        / "EXP_2026-08-04_phase4_e14_bounded_exhaustion.md"
    ).read_text()
    canon = (
        ROOT
        / "ObsidianVault"
        / "Canon"
        / "Memory"
        / "MEM_80089938_actor_berry_column_state_table.md"
    ).read_text()
    assert "bounded-exhausted" in note
    assert "0x8004B4F4" in note
    assert "Lazy berry-column inheritance" in canon

"""Guard the evidence boundary for the player grounded flag at 0x800A6582."""

import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "analysis/phase4_grounded_flag_census.json"
CANON = ROOT / "ObsidianVault/Canon/Functions/FUNC_8003633C_player_movement_+_collision_integrator.md"
SOURCE = ROOT / "src_re/movement_integrator_8003633c.c"
MOVEMENT_SYSTEM = ROOT / "ObsidianVault/Canon/Systems/SYS_movement_and_physics.md"
PLAYER_SYSTEM = ROOT / "ObsidianVault/Canon/Systems/SYS_player.md"
PLAYER_UPDATE = ROOT / "src_re/player_update_80048138.c"


@pytest.fixture(scope="module")
def fresh_census(tmp_path_factory):
    out = tmp_path_factory.mktemp("grounded") / "census.json"
    subprocess.run(
        ["python", "tools/census_address.py", "0x800A6582", "--bytes", "2",
         "--block", "0x800A6500", "--json", str(out)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(out.read_text())


def test_general_census_reproduces_the_banked_direct_sets_and_residual(fresh_census):
    banked = json.loads(CENSUS.read_text())
    for key in ("writers", "readers", "residual"):
        assert fresh_census[key] == banked[key]
    assert len(banked["writers"]) == 16
    assert all(x["insn"].startswith("sh zero,") for x in banked["writers"])
    assert banked["residual"]["unresolved_accesses_total"] == 12956
    assert banked["residual"]["unresolved_same_width_in_related_functions"] == 450
    assert banked["residual"]["indirect_calls_unresolved"] == 149


@pytest.mark.parametrize("path", [CANON, SOURCE])
def test_sole_setter_and_false_exact_pc_do_not_return(path):
    text = path.read_text()
    flat = " ".join(text.split())
    assert "collision-resolution path is the ONLY producer" not in text
    assert "grounded SET inside this function's region, ~0x80036cbc" not in text
    assert "exact producer is not established" not in flat
    assert "0x80036CB8 plus the 0x80036CC0 delay slot" in flat
    assert "global exclusivity is not" in flat
    assert "ONLY-producer claim" in flat and "is retracted" in flat


@pytest.mark.parametrize("path", [CANON, SOURCE])
def test_corrected_pseudocode_matches_the_pinned_branch_and_two_byte_set(path):
    text = path.read_text()
    flat = " ".join(text.split())
    assert "code != 2 && (path_result == 1 || code == 1)" in flat
    assert "flag[1] = (unsigned char)1" in text
    assert "if (code == 2)" not in text
    assert "Earlier pseudocode wrote" in flat and "that was wrong" in flat


def test_clean_live_restatements_use_the_exact_producer_without_exclusivity():
    movement = " ".join(MOVEMENT_SYSTEM.read_text().split())
    player = " ".join(PLAYER_SYSTEM.read_text().split())
    source = " ".join(PLAYER_UPDATE.read_text().split())
    assert "sole producer of `grounded = 0x0101`" not in movement
    assert "0x80036CB8" in movement and "global producer exclusivity is not established" in movement
    assert "global producer exclusivity" in player
    assert "ONLY when native collision reports ground contact" not in source
    assert "around 0x80036cbc/0x80036cd0/ 0x80036b90" not in source
    assert "0x80036CB8" in source and "0x80036CC0" in source

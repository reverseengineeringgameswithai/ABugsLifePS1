"""Pristine-image pins and negative guards for three audited closure overclaims."""

import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_integrity_scope_guard.c"
ARENA_CENSUS = ROOT / "analysis/phase4_arena_limit_census.json"
ARENA_MATERIALIZATIONS = ROOT / "analysis/phase4_arena_constant_materializations.json"
CONTACT_CENSUS = ROOT / "analysis/phase4_contact_flag_record0_census.json"
ARENA_CANON = ROOT / "ObsidianVault/Canon/Functions/FUNC_800313A8_collision_grid_builder.md"
ARENA_SOURCE = ROOT / "src_re/collision_grid_builder_800313a8.c"
CONTACT_CANON = ROOT / "ObsidianVault/Canon/Systems/SYS_contact_object_pool.md"


@pytest.fixture(scope="module")
def pin_report(tmp_path_factory):
    exe = tmp_path_factory.mktemp("scope_guard") / "scope_guard"
    subprocess.run(
        ["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
         str(TOOL), "-lcrypto", "-o", str(exe)],
        cwd=ROOT,
        check=True,
    )
    run = subprocess.run([str(exe)], cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(run.stdout)


def test_compiled_guard_pins_the_exact_pristine_facts(pin_report):
    assert pin_report["instruction_pins"] == 49
    assert pin_report["grounded_player_call"] == {
        "producer_pcs": ["0x80036CB8", "0x80036CC0"],
        "value": "0x0101",
        "global_exclusivity": False,
    }
    assert pin_report["arena_limit"] == {
        "resolved_writers": ["0x8003C2F4"],
        "resolved_readers": ["0x800313B8", "0x8003D5D8"],
        "value": "0x801CC390",
    }
    assert pin_report["contact_flag"]["currently_resolved_post_creation_stores"] == [
        "0x800588AC", "0x80058F74",
    ]
    assert pin_report["contact_flag"]["complete_census"] is False


def test_arena_general_census_retains_the_residual():
    doc = json.loads(ARENA_CENSUS.read_text())
    assert [x["pc"] for x in doc["writers"]] == ["0x8003C2F4"]
    assert [x["pc"] for x in doc["readers"]] == ["0x800313B8", "0x8003D5D8"]
    assert doc["residual"]["unresolved_accesses_total"] == 12956
    assert doc["residual"]["unresolved_same_width_in_related_functions"] == 105
    assert doc["residual"]["indirect_calls_unresolved"] == 149


def test_arena_materialisation_count_is_fourteen_total_not_fourteen_other():
    doc = json.loads(ARENA_MATERIALIZATIONS.read_text())
    assert doc["sites_inside"] == 14
    pcs = [x["pc"] for x in doc["sites"] if x["kind"] == "ADDR_TAKE"]
    assert "0x8003C2F0" in pcs
    assert len(pcs) == 14


@pytest.mark.parametrize("path", [ARENA_CANON, ARENA_SOURCE])
def test_arena_only_writer_and_off_by_one_count_do_not_return(path):
    text = path.read_text()
    flat = " ".join(line.lstrip(" *").strip() for line in text.splitlines())
    assert "the ONLY writer of the arena" not in text
    assert "14 other code sites" not in text
    assert "only statically resolved direct writer" in flat
    assert "13 other resolved fixed-form materialisations" in flat


def test_contact_sites_are_pinned_without_an_exact_global_count():
    census = json.loads(CONTACT_CENSUS.read_text())
    assert [x["pc"] for x in census["writers"]] == ["0x80058F74"]
    assert census["residual"]["unresolved_accesses_total"] == 12956
    assert census["residual"]["unresolved_same_width_in_related_functions"] == 6
    assert census["residual"]["indirect_calls_unresolved"] == 149
    text = CONTACT_CANON.read_text()
    flat = " ".join(text.split())
    assert "written after creation at exactly two sites" not in text
    assert "can therefore never acquire one" not in text
    assert "Two post-construction stores" in flat
    assert "not a complete field-aware writer census" in flat

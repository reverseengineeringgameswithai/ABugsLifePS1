import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_player_state_writer_pins.c"
CANON = ROOT / "ObsidianVault/Canon/Systems/SYS_player_action_state_laws.md"


def test_pristine_writer_pins_match_the_general_census(tmp_path):
    binary = tmp_path / "player_state_writer_pins"
    build = subprocess.run(
        ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
         str(TOOL), "-o", str(binary), "-lcrypto"],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result["resolved_direct_writers"] == 19
    assert result["resolved_direct_value_3_writers"] == ["0x80048CFC"]
    assert len(result["writer_pcs"]) == len(set(result["writer_pcs"])) == 19
    assert result["instruction_pins"] == 36


def test_canon_does_not_restore_the_ten_site_complete_map():
    text = CANON.read_text()
    prose = " ".join(text.split())
    assert "Complete writer map, for reference" not in text
    assert "3 is written by exactly one instruction" not in text
    assert "sole value-3 producer among resolved direct writers" in prose
    assert "12,956 unresolved-base accesses" in text

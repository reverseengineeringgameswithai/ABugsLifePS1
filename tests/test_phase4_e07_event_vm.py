"""Guards for the E07 (event VM / scripted objects) evidence.

See ObsidianVault/Experiments/EXP_2026-08-02_phase4_e07_bounded_exhaustion.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
BOUNDED = ROOT / "analysis" / "phase4_e07_bounded_exhaustion.json"
STAGE_JOIN = ROOT / "analysis" / "phase4_e07_stage_join.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_bounded():
    return json.loads(BOUNDED.read_text())


def load_stage_join():
    return json.loads(STAGE_JOIN.read_text())


def test_move_on_verdict_not_strict_complete():
    doc = load_bounded()
    assert doc["move_on_verdict"] == "sufficiently_bounded_exhausted"
    assert doc["strict_phase4_complete"] is False


def test_resident_isa_and_corpus_closed():
    doc = load_bounded()
    frontiers = doc["closed_frontiers"]
    assert "26/26" in frontiers["resident_interpreter_isa"]
    assert "40 entries, 421 decoded instructions" in frontiers["authored_program_corpus"]
    assert "zero invalid opcodes" in frontiers["authored_program_corpus"]


def test_five_applicable_overlay_natives_named():
    doc = load_bounded()
    natives = doc["applicable_overlay_natives"]
    assert len(natives) == 5
    slots = {n["slot"] for n in natives}
    assert slots == {3, 4, 5, 6, 9}


def test_stage_join_confirms_17_of_20_and_37_of_40():
    doc = load_stage_join()
    assert doc["campaign"]["actor_table_found"] == 17
    assert doc["campaign"]["stage_pairs"] == 20
    assert doc["campaign"]["out_of_40_range"] == []


def test_movie_not_required_now():
    doc = load_bounded()
    assert doc["movie_required_now"] is False


def test_static_tools_reproduce_their_cited_findings():
    import subprocess
    import tempfile

    for name in ("phase4_e07_static.c", "phase4_e07_capsule.c", "phase4_e07_deep_static.c"):
        src = ROOT / "tools" / name
        with tempfile.NamedTemporaryFile(suffix="") as out:
            result = subprocess.run(
                ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                 str(src), "-o", out.name, "-lcrypto"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"{name} failed to compile: {result.stderr}"

    for name in ("phase4_e07_stage_join.c", "phase4_e07_callback_disasm.c"):
        src = ROOT / "tools" / name
        with tempfile.NamedTemporaryFile(suffix="") as out:
            result = subprocess.run(
                ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                 str(src), "-o", out.name],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"{name} failed to compile: {result.stderr}"


def test_registry_status_is_partial_with_bounded_next():
    text = REGISTRY.read_text()
    start = text.index("  - id: E07_event_vm")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "E07_event_vm"
    assert row["status"] == "partial"
    assert "BOUNDED 2026-08-03" in row["next"]
    assert "EVIDENCE BANKED 2026-08-03" in " ".join(row["bindings"])

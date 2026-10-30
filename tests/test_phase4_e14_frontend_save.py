"""Guards for the E14 (frontend/save) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_e14_frontend_save.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_e14_frontend_save.json"
SERIALIZER_SRC = ROOT / "src" / "main" / "80055478_serialize_savegame_buffer.c"
INIT_SRC = ROOT / "src" / "main" / "80055414_scene_flow_state_table_init.c"
APPLY_SRC = ROOT / "src" / "main" / "80055538_scene_config_apply.c"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_schema_layout_matches_the_byte_matched_sources():
    ser = SERIALIZER_SRC.read_text()
    init = INIT_SRC.read_text()
    apply_ = APPLY_SRC.read_text()
    # serializer: lives, progress, 19 bytes, 64x5 from offset 28
    assert "g_800a65a0" in ser and "g_80082284" in ser
    assert "i < 19" in ser
    assert "i < 320" in ser and "i + 28" in ser
    # init defaults {5,1} and {100,255,255,255,255}
    assert "p[0] = 5" in init and "p[1] = 1" in init
    assert "r[28] = 100" in init and "r[29] = 255" in init
    # apply consumes the serializer-gap fields
    assert "cfg[22]" in apply_ and "cfg[23]" in apply_
    assert "cfg + 24" in apply_ and "cfg + 26" in apply_


def test_apply_gap_consumers_are_named():
    doc = load_artifact()
    schema = doc["SAVE_SCHEMA_MAPPED_2026-08-03"]
    assert "cd_mix_shim" in schema["layout"]["bytes_21_27"]
    assert "set_draw_env_offset" in schema["layout"]["bytes_21_27"]


def test_side_table_indexing_and_owners():
    doc = load_artifact()
    side = doc["SIDE_TABLE_DECODED_2026-08-03"]
    assert "table[actor_id*5 + equipped_berry_index]" in side["what_it_is"]
    assert "0x800A6597" in side["what_it_is"]
    owners = side["instruction_level_owners"]
    assert "0x8004B258" in owners["ko_decrement"]
    assert "0x40" in owners["ko_decrement"]
    assert "FUNC_80049C30" in owners["respawn_clamp_and_aggro_gate"]
    assert "NOT claimed" in owners["respawn_clamp_and_aggro_gate"] or "not claimed" in owners["respawn_clamp_and_aggro_gate"]


def test_cross_save_deviations_match_the_d01_roster():
    doc = load_artifact()
    side = doc["SIDE_TABLE_DECODED_2026-08-03"]
    diff = side["empirical_cross_save_diff"]
    # the exact roster set, cross-checked against D01's artifact
    d01 = json.loads((ROOT / "analysis" / "phase4_d01_enemy_spawn_update.json").read_text())
    bound = set(int(k) for k in d01["ID_ROSTER_RECONCILIATION_2026-08-03"]["newly_bound_from_the_36_unknowns"])
    canyon = {6, 9, 10, 12, 13, 15, 17, 18, 22, 29, 30, 34, 37, 39, 40, 41}
    assert canyon <= bound
    assert str(sorted(canyon)).replace(" ", "").strip("[]") in diff.replace(" ", "") or "6,9,10,12,13,15,17,18,22,29,30,34,37,39,40,41" in diff


def test_hidden_mechanic_flagged_with_open_direction():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "increment source" in still_open
    assert "live A/B" in still_open


def test_registry_row_updated():
    text = REGISTRY.read_text()
    start = text.index("  - id: E14_frontend_save")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "E14_frontend_save"
    assert row["status"] == "partial"
    joined = " ".join(row["bindings"])
    assert "SAVE SCHEMA MAPPED 2026-08-03" in joined
    assert "SIDE TABLE DECODED 2026-08-03" in joined
    assert "bounded 2026-08-03" in row["next"]

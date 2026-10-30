import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_chunk33_collision_tail_boundary():
    roles = json.loads((ROOT / "tools" / "level_raw_chunk_roles.json").read_text())
    chunk32 = next(row for row in roles if row["chunk"] == 32)
    chunk33 = next(row for row in roles if row["chunk"] == 33)

    array_offset = 0x36570
    stride = 0x4C
    count = 223
    assert chunk32["decomp"] - array_offset == 189 * stride + 4
    assert array_offset + count * stride - chunk32["decomp"] == 0xA14
    assert chunk33["confidence"] == "CONFIRMED"
    assert "sectors 189-222" in chunk33["role"]


def test_loose_end_evidence_is_closed_at_the_claimed_scope():
    evidence = json.loads((ROOT / "analysis" / "loose_ends.json").read_text())
    assert evidence["items"]["mover_vm_op11"]["status"] == "confirmed_static"
    assert evidence["items"]["level_raw_chunk33"]["status"] == "confirmed_static"
    assert evidence["items"]["scene_hud_globals"]["status"] == "address_role_closed"

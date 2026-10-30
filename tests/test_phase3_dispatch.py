"""Phase-3 WP4 guard: the indirect-dispatch map is consistent and fresh.

Offline checks always run; byte-level regeneration needs the local EXE
(local_media)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "analysis" / "phase3_dispatch_map.json").read_text())


def test_tables_present_and_fully_resolved():
    tables = DOC["tables"]
    assert set(tables) == {"mover_vm_opcodes", "berry_throw", "plant_behaviors"}
    assert len(tables["mover_vm_opcodes"]["targets"]) == 26
    assert len(tables["berry_throw"]["targets"]) == 5
    assert len(tables["plant_behaviors"]["targets"]) == 13
    assert DOC["gaps"] == []
    for name, t in tables.items():
        for e in t["targets"]:
            assert e.get("name"), (name, e)
            assert e["target"].startswith("0x8004") or \
                e["target"].startswith("0x8005"), (name, e)


def test_known_bindings_hold():
    """Cross-check against independently established Canon facts."""
    vm = {e["index"]: e for e in DOC["tables"]["mover_vm_opcodes"]["targets"]}
    # op9 was mislabeled "move" by an early symbol; u2 pinned it as
    # branch_if_s3 — either way it must be a distinct named handler
    assert vm[9]["name"] not in (None, "mover_vm_dispatch_next")
    plant = {e["index"]: e for e in DOC["tables"]["plant_behaviors"]["targets"]}
    # index = type-2: trampoline(5)->3, propeller(3)->1, dandelion(8)->6,
    # cannon(2)->0, green passive(4)->2 per Canon brown/green seed notes
    assert plant[3]["name"] == "seed_plant_trampoline_handler"
    assert plant[1]["name"] == "seed_plant_propeller_handler"
    assert plant[6]["name"] == "seed_plant_dandelion_handler"
    assert plant[0]["name"] == "seed_plant_cannon_handler"
    assert plant[2]["target"] == "0x8005CCE8"      # green passive-collision
    berry = DOC["tables"]["berry_throw"]["targets"]
    assert len({e["target"] for e in berry}) == 5  # five distinct entry offsets


def test_indirect_site_inventory():
    inv = DOC["indirect_sites"]
    assert inv["total"] == inv["jalr"] + inv["jr_table_dispatch"]
    assert inv["total"] == len(inv["sites"])
    # the VM interpreter's dispatch jr must be attributed to its decoded table
    vm = [x for x in inv["sites"] if x["pc"] == "0x8004C220"]
    assert vm and vm[0]["table"] == "mover_vm_opcodes"
    for x in inv["sites"]:
        assert x["kind"] in ("jr", "jalr")
        assert x["reg"] != 31 or x["kind"] == "jalr"
    assert inv["jr_with_decoded_table"] >= 1


@pytest.mark.local_media
def test_map_is_fresh_regeneration():
    before = json.loads((ROOT / "analysis" / "phase3_dispatch_map.json").read_text())
    proc = subprocess.run([sys.executable, "tools/phase3_dispatch_map.py"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    after = json.loads((ROOT / "analysis" / "phase3_dispatch_map.json").read_text())
    before.pop("generated"), after.pop("generated")
    assert before == after, "committed dispatch map is stale"

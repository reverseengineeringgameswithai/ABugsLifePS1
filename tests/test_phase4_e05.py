"""Phase-4 E05 (actor models and animation): machine-checkable gates.

Covers the two committed artifacts:
  analysis/phase4_e05_model_binding_static.json  (EXE-decoded id -> model path)
  analysis/phase4_e05_model_pointers_live.json   (16-level runtime confirmation)
plus regeneration determinism of the static extractor against the pristine EXE.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "analysis/phase4_e05_model_binding_static.json"
LIVE = ROOT / "analysis/phase4_e05_model_pointers_live.json"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"

POINTER_ARRAY = 0x800A6300
PLANT_TABLE_CANON = 0x800A649C
PLANT_ID_BIAS = 103

# Curated committed species bindings (D01 roster / per-species rows) vs decoded
# path basenames. These are exact-known pairs only.
SPECIES_PATH = {
    6: "fly", 9: "badbug", 10: "mos", 12: "grub", 13: "wasp", 15: "ggrassh",
    17: "hspider", 19: "roach", 22: "hopper", 29: "molt", 30: "bbird",
    34: "dragfly", 37: "weevil", 40: "badworm",
}

# Scene words read live, cross-checked against committed scene claims
# (C15: Cliffside == scene 6) and the Flik-variant sets decoded from the EXE.
SCENE_EXPECT = {
    "stage04_cliffside_canyon": 6,
    "stage02_tunnels": 3,
    "stage03_council_chamber": 2,
    "stage07_city_entrance": 4,
    "stage08_city_square": 5,
}


def _static():
    return json.loads(STATIC.read_text())


def _live():
    return json.loads(LIVE.read_text())


def test_static_artifact_pins_the_pristine_exe():
    d = _static()
    assert d["exe_sha256"] == hashlib.sha256(EXE.read_bytes()).hexdigest()
    assert d["consistency_problems"] == []


def test_static_table1_is_complete_and_self_consistent():
    d = _static()
    rows = d["table1_actor_models"]
    assert len(rows) == 41
    for r in rows:
        assert r["path"], r
        assert r["model_id"] == r["actor_id"], r
        assert r["ptr_slot"] == r["actor_id"], r
        assert int(r["pointer_global"], 16) == POINTER_ARRAY + 4 * r["actor_id"]
    # id 11 (seed) is the single special-cased loader in table1
    specials = {r["actor_id"]: r["callee"] for r in rows if r["callee"] not in (None, "0x8005d654")}
    assert specials == {11: "0x8005d924"}
    assert rows[10]["path"] == "bits\\seed"


def test_static_table2_is_the_canon_plant_window():
    d = _static()
    rows = d["table2_plant_models"]
    assert len(rows) == 14
    for r in rows:
        n = r["plant_type"]
        assert r["model_id"] == PLANT_ID_BIAS + n
        assert r["path"].endswith(f"plant{n:02d}"), r
        # slot arithmetic: 0x800A6300 + 4*(103+N) == Canon plant table 0x800A649C + 4*N
        assert POINTER_ARRAY + 4 * (PLANT_ID_BIAS + n) == PLANT_TABLE_CANON + 4 * n


def test_static_species_join_matches_committed_roster():
    d = _static()
    by_id = {r["actor_id"]: r["path"] for r in d["table1_actor_models"]}
    for aid, base in SPECIES_PATH.items():
        assert by_id[aid].split("\\")[-1] == base, (aid, by_id[aid])


def test_extractor_regenerates_identically(tmp_path):
    out = tmp_path / "regen.json"
    r = subprocess.run([sys.executable, str(ROOT / "tools/phase4_e05_model_binding_extract.py"),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    regen = json.loads(out.read_text())
    cur = _static()
    for key in ("table1_actor_models", "table2_plant_models", "flik_variants_by_scene"):
        assert regen[key] == cur[key]


def test_live_confirms_registry_on_all_16_levels():
    d = _live()
    assert d["failing_levels"] == []
    levels = d["levels"]
    assert len(levels) == 16
    for label, r in levels.items():
        assert "error" not in r, (label, r)
        assert r["ok"], label
        nonnull = set(r["nonnull_slots"])
        pool = set(r["pool_distinct_ids"])
        plants = {s for s in nonnull if 104 <= s <= 117}
        # the registry holds EXACTLY flik + this level's pool ids + its plants
        assert nonnull == {0} | pool | plants, label
        # second registry: never a slot without a model, never a differing pointer
        assert r["anm_without_model"] == [], label
        assert r["second_registry_differs_model_ptr"] == [], label
        # only the seed (11) and sometimes flik (0) lack a second-registry entry
        assert set(r["model_without_anm"]) <= {0, 11}, label


def test_live_scene_words_match_committed_claims():
    d = _live()
    for label, scene in SCENE_EXPECT.items():
        assert d["levels"][label]["scene_word"] == scene, label

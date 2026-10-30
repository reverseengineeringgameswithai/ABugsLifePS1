"""Phase-4 E03 (render ordering and packets): machine-checkable gates.

Covers the four committed artifacts:
  analysis/phase4_e03_ot_packet_census.json      (gp0Trace census, 4 scene classes)
  analysis/phase4_e03_ot_walk_crosscheck.json    (C walker vs gp0Trace, 3 scenes)
  analysis/phase4_e03_emitter_roster.json        (prim-cursor write-watch roster)
  analysis/phase4_e03_transparency_modes.json    (blend-mode distribution)
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "analysis/phase4_e03_ot_packet_census.json"
CROSS = ROOT / "analysis/phase4_e03_ot_walk_crosscheck.json"
ROSTER = ROOT / "analysis/phase4_e03_emitter_roster.json"
TRANS = ROOT / "analysis/phase4_e03_transparency_modes.json"

BUF_A = "0x801e134c"
BUF_B = "0x801cc390"
STATIC_NODE_LO = "0x8007fc88"
BUCKET_TABLE_ENTRIES = 1228

# Present in EVERY captured scene class. Gameplay/boss additionally use
# shared_all_mesh_renderer + object_mesh_draw; training routes skinned meshes
# through bone_matrix_array_mesh_transform instead (recorded in the roster).
CORE_EMITTERS_ALL_SCENES = {
    "frame_present",
    "per_object_mesh_draw_payload_emitter",
    "dirt_mesh_builder",
    "contact_record_billboard_render",
    "hud_draw_glyph",
    "ot_depth_fade_postprocess",
}
GAMEPLAY_EXTRA = {"shared_all_mesh_renderer", "object_mesh_draw"}


def _load(p):
    return json.loads(p.read_text())


def test_census_covers_all_four_scene_classes():
    d = _load(CENSUS)
    assert set(d["scenes"]) == {"normal_gameplay", "boss_showdown", "fmv", "training"}
    for lbl, s in d["scenes"].items():
        assert "error" not in s, (lbl, s.get("error"))
        assert s["captured_frames"] == 4, lbl
        assert not s["trace_truncated"], lbl
        for fr in s["frames"]:
            assert fr["dma"] + fr["mmio"] == fr["total"], lbl


def test_census_double_buffering_is_lockstep():
    """OT-active pointer and displayed VRAM rect flip together, per rendered
    frame, in every 3D scene; FMV never flips the OT pointer."""
    d = _load(CENSUS)
    for lbl in ("normal_gameplay", "boss_showdown", "training"):
        frames = d["scenes"][lbl]["frames"]
        ptrs = [f["meta"]["ot_active_ptr"] for f in frames]
        xs = [f["meta"]["vram_source_rect"][0] for f in frames]
        assert set(ptrs) == {BUF_A, BUF_B}, lbl
        assert set(xs) == {0, 512}, lbl
        # meta is sampled per vsync at 30 fps: values come in pairs and the
        # pointer + displayed rect flip TOGETHER at the rendered-frame boundary
        assert ptrs[0] == ptrs[1] != ptrs[2] == ptrs[3], lbl
        assert xs[0] == xs[1] != xs[2] == xs[3], lbl
    fmv = d["scenes"]["fmv"]["frames"]
    assert len({f["meta"]["ot_active_ptr"] for f in fmv}) == 1
    assert fmv[0]["meta"]["display_24bpp"] is True


def test_census_packet_lifetime_only_static_node_recurs():
    """Adjacent rendered frames (opposite buffers) share EXACTLY the 4-command
    static node at 0x8007FC88; same-buffer pairs additionally share a
    deterministic allocation prefix (same reset cursor, similar content)."""
    d = _load(CENSUS)
    for lbl in ("normal_gameplay", "boss_showdown", "training"):
        for rec in d["scenes"][lbl]["addr_recurrence"]:
            adjacent = rec["frames"][1] - rec["frames"][0] == 2
            if adjacent:  # opposite buffers at 30 fps
                assert rec["shared"] == 4, (lbl, rec)
            else:         # same buffer two rendered frames apart
                assert rec["shared"] >= 4, (lbl, rec)
            assert rec["shared_clusters"][0]["lo"] == STATIC_NODE_LO, lbl


def test_census_fmv_regime():
    d = _load(CENSUS)
    for fr in d["scenes"]["fmv"]["frames"]:
        fams = fr["families"]
        assert set(fams) <= {"clear_cache", "cpu_to_vram_blit", "env_texpage",
                             "env_texwindow", "env_draw_area_tl",
                             "env_draw_area_br", "env_draw_offset", "env_mask"}, fams
        assert fams.get("cpu_to_vram_blit") == fams.get("clear_cache") == 20, fams


def test_crosscheck_walker_equals_trace_everywhere():
    d = _load(CROSS)
    assert d["failing"] == []
    assert set(d["scenes"]) == {"normal_gameplay", "boss_showdown", "training"}
    for lbl, s in d["scenes"].items():
        assert s["ok"], lbl
        assert s["opcode_mismatches"] == {}, lbl
        assert s["walk"]["packets"] == s["trace_body_cmds"], lbl
        assert s["walk"]["terminated"] in (True, "true"), lbl
        assert s["walk"]["empty_link_nodes"] == BUCKET_TABLE_ENTRIES, lbl


def test_walker_compiles():
    subprocess.run(["cc", "-O2", "-fsyntax-only",
                    str(ROOT / "tools/phase4_e03_ot_walk.c")], check=True)


def test_emitter_roster_core_set_and_reset_owner():
    d = _load(ROSTER)
    for lbl, s in d["scenes"].items():
        syms = {r.get("symbol") for r in s["sites"]}
        assert CORE_EMITTERS_ALL_SCENES <= syms, (lbl, CORE_EMITTERS_ALL_SCENES - syms)
        bucket_writers = {r.get("symbol") for r in s["sites"]
                         if r["target"] == d["bucket_base"]}
        assert bucket_writers == {"frame_present"}, (lbl, bucket_writers)
    for lbl in ("normal_gameplay", "boss_showdown"):
        syms = {r.get("symbol") for r in d["scenes"][lbl]["sites"]}
        assert GAMEPLAY_EXTRA <= syms, lbl
    training = {r.get("symbol") for r in d["scenes"]["training"]["sites"]}
    assert "bone_matrix_array_mesh_transform" in training


def test_transparency_modes_account_for_every_semitrans_prim():
    d = _load(TRANS)
    census = _load(CENSUS)
    for lbl, s in d["scenes"].items():
        assert s["all_semitrans_are_textured_polys"], lbl
        assert sum(s["textured_semitrans_prim_modes"].values()) == s["semitrans_prims"], lbl
        # census frame 0 of the same scene agrees on the semitrans count scale
        f0 = census["scenes"][lbl]["frames"][0]
        assert abs(f0["semitrans_prims"] - s["semitrans_prims"]) <= 40, lbl

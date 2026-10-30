"""Phase-4 E16: the pointer-registered LEVEL.RAW chunks and their consumers.

Covers analysis/phase4_e16_registered_chunks.json (static format) and
analysis/phase4_e16_table_read_watch.json (the live run that found the readers).

The row's last open item was "find the consumers of 0x8009B4E8 / 0x8009C170 /
0x800A6450", because the loader registers 46 chunks by pointer and never
interprets them -- so their format belongs to whoever reads the tables. These
gates pin the answer and, just as importantly, keep the two wrong turns taken on
the way to it visible.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FMT = ROOT / "analysis/phase4_e16_registered_chunks.json"
WATCH = ROOT / "analysis/phase4_e16_table_read_watch.json"
LIFETIME_GUARD = ROOT / "tools/phase4_e16_table_lifetime_guard.c"
TABLE_PAGE = ROOT / "ObsidianVault/Canon/Memory/MEM_8009B4E8_registered_chunk_table_0x30_0x57.md"
SYSTEM_PAGE = ROOT / "ObsidianVault/Canon/Systems/SYS_registered_chunk_image_resources.md"


def _fmt():
    return json.loads(FMT.read_text())


def _watch():
    return json.loads(WATCH.read_text())


def test_tools_compile():
    for src in ("tools/phase4_e16_image_header.c",
                "tools/phase4_e16_table_consumers.c",
                "tools/mips_ea_window.c"):
        subprocess.run(["cc", "-O2", "-Werror", "-fsyntax-only", str(ROOT / src)], check=True)


def test_all_46_registered_chunks_obey_a_consumer_derived_size_law():
    """The whole point: no free parameters. Each chunk's size is predicted by the
    layout its own consumer reads, and every one of the 46 matches exactly."""
    c = _fmt()["counts"]
    assert c["chunks"] == 46
    assert c["size_law_holds"] == 46
    assert c["by_family"] == {"B_markers_0x30_0x5F": 43, "A_markers_0x28_0x2F": 3}
    assert c["by_depth_bpp"] == {"4": 3, "8": 40, "16": 3}


def test_two_families_match_two_distinct_consumer_access_patterns():
    """Family A is read with 32-bit loads and its payload starts at +16; family B
    is read with 16-bit loads and its payload starts at +12. The split is in the
    code, not chosen to make the arithmetic work."""
    f = _fmt()["format"]
    a, b = f["family_A_markers_0x28_0x2F"], f["family_B_markers_0x30_0x5F"]
    assert "size == 16 + width*height*2" == a["size_law"]
    assert "lw v0,4(s4)" in a["derivation"] and "addiu a1,s4,16" in a["derivation"]
    assert "lhu" in b["derivation"] and "+12" in b["derivation"]
    assert "depth_flag 1 = 8bpp, 0 = 4bpp" in b["pixels"]


def test_family_a_32bit_fields_explain_the_apparent_zero_height():
    """Read as u16, family A's width/height look like a 0 height and a 0 depth
    flag. That trap must stay documented -- it is what made 6 chunks look
    malformed under a single-family reading."""
    f = _fmt()["format"]
    assert "high halves" in f["why_family_A_looked_malformed"]
    rows = [r for r in _fmt()["rows"] if r.get("ok") and r["family"].startswith("A_")]
    assert len(rows) == 3
    for r in rows:
        assert r["u16_at_6"] == 0 and r["u16_at_10"] == 0   # the misleading halves
        assert r["height"] == r["u32_at_8"] > 0             # the real field


def test_consumers_are_named_and_reach_the_vram_upload_primitives():
    consumers = " ".join(c["reader"] for c in _fmt()["consumers"])
    assert "level_texture_stage@0x8003c920" in consumers
    assert "vram_upload_wait@0x8003c3c0" in consumers
    assert "vram_upload_wait@0x8003c5ec" in consumers
    assert "LoadImage" in consumers and "level_texture_upload" in consumers


def test_slot_addressing_uses_the_raw_marker():
    """slot = DISP_BASE + marker*4, NOT (marker - range_lo)*4. Getting this wrong
    points a watch at 160 bytes entirely below the table, where the loader's own
    stores never fire -- which is exactly what happened on the first live run."""
    assert "marker*4" in _fmt()["slot_addressing"]
    assert "RAW marker" in _fmt()["slot_addressing"]
    for c in _fmt()["consumers"]:
        lo = int(c["markers"].split("..")[0], 16)
        base = int(c["table_disp_base"], 16)
        assert int(c["true_window"].split("..")[0], 16) == base + lo * 4


def test_live_run_found_the_readers_with_a_passing_positive_control():
    """A negative from this watch would only be worth as much as its control, so
    the loader's own registration stores had to appear in the same run."""
    w = _watch()
    assert w["positive_control_ok"] is True
    assert w["write_count"] > 0 and w["read_count"] > 0
    assert w["truncated"] is False              # no events were dropped
    per = w["per_table"]
    assert len(per) == 3
    for v in per.values():
        assert v["writes"] > 0                  # every table is registered into
    # every table is read by exactly one site
    readers = {pc for v in per.values() for pc in v["read_pcs"]}
    assert readers == {"0x8003c3c4", "0x8003c5f0", "0x8003c924"}


def test_static_displacement_scan_alone_could_not_have_found_them():
    """The reason this needed a live watch. The consumers index the table
    (`lui at,0x800A; addu at,at,idx; lw v0,DISP(at)`), so their displacement is
    not the table base and a base-displacement scan misses them -- the 0x30..0x57
    reader sits at -19032, outside the [-19224,-19064] base window."""
    win = (ROOT / "tools/mips_ea_window.c").read_text()
    assert "INDEXED" in win                       # the tool reports the indexed form
    assert "misses the access entirely" in win    # and says why the scan fails
    scan = (ROOT / "tools/phase4_e16_table_consumers.c").read_text()
    assert "base-only matching misses entirely" in scan
    census = json.loads((ROOT / "analysis/phase4_e16_chunk_census.json").read_text())
    why = census["REGISTERED_CHUNKS_RESOLVED_2026-08-04"]["why_a_static_scan_could_not_settle_it"]
    assert "-19032" in why and "clean negative was" in why


def test_earlier_not_images_correction_is_itself_corrected():
    """I corrected 'all 74 unknowns are images' to 'the 46 are NOT images'. The
    46 ARE images -- uploaded later by a different path. The over-correction has
    to be visible, not quietly replaced."""
    census = json.loads((ROOT / "analysis/phase4_e16_chunk_census.json").read_text())
    r = census["REGISTERED_CHUNKS_RESOLVED_2026-08-04"]
    assert "over-corrected" in r["CORRECTION_to_my_own_correction"]
    assert "46/46" in r["result"]
    assert "0x8003c920" in json.dumps(r)


def test_decoder_renders_named_retail_resources():
    """End-to-end: the layout is confirmed by the images rendering as real art,
    which is what rules out a plausible-but-wrong header reading."""
    d = _fmt()["visual_confirmation"]
    assert d["LEVEL00/LEVEL.RAW marker 0x43"].startswith("memory-card UI text atlas")
    assert "title screen" in d["LEVEL00/LEVEL3.RAW marker 0x28"]
    assert "not committed" in d["note"].lower()  # copyrighted art stays out of the repo


def test_all_registered_chunks_are_frontend_resources():
    """Every one of the 46 lives in LEVEL00 -- the frontend. That is why the
    boot -> menu -> level-select movie was the right run to watch."""
    files = {r["file"] for r in _fmt()["rows"] if r.get("ok")}
    assert files and all(f.startswith("LEVEL00/") for f in files)


def test_family_b_upload_path_is_read_end_to_end():
    """The depth flag's consumer, the rect, and the pixel-source rule -- all read
    from level_texture_stage rather than inferred from the data."""
    u = _fmt()["upload_path_family_B_2026-08-04"]
    assert "0x8003CB54" in u["depth_flag_consumer"]
    assert "(w+3)>>2" in u["depth_flag_consumer"] and "w>>1" in u["depth_flag_consumer"]
    assert "0x80089848" in u["rect"]
    assert "palette_bytes & ~1" in u["pixel_source"]
    # independently reproduces the rule already pinned for the texture-page path
    assert "round_down_even" in u["pixel_source"]


def test_pure_green_is_the_preserved_colour_key():
    """The palette is scaled to 75% except the key colour. Scaling the key would
    turn 255 into 191 and stop it matching -- which is why the exception exists."""
    u = _fmt()["upload_path_family_B_2026-08-04"]
    assert "R<5 AND G>=250 AND B<5" in u["colour_key"]
    assert "(0,255,0)" in u["colour_key"]
    assert "(v*96)>>7" in u["palette_pipeline"]
    assert "THREE BYTES AT A TIME" in u["palette_pipeline"]   # proves 256 x RGB888


def test_the_wrong_depth_lead_stays_recorded():
    """I named `andi v0,v0,3` as the 4bpp/8bpp lead; it is an alignment test. A
    plausible instruction near the code you happen to be reading is not evidence
    about a question you have not yet located."""
    u = _fmt()["upload_path_family_B_2026-08-04"]
    c = u["CORRECTION_earlier_lead"]
    assert "0x8003C954" in c and "WRONG" in c and "ALIGNMENT" in c


def test_dimmed_clut_is_labelled_a_reading_not_a_finding():
    u = _fmt()["upload_path_family_B_2026-08-04"]
    assert "READING, not established" in u["two_clut_uploads"]


# ---- resource ownership / lifetime (analysis/phase4_e16_resource_lifetime.json) ----

LIFE = ROOT / "analysis/phase4_e16_resource_lifetime.json"


def _life():
    return json.loads(LIFE.read_text())


def test_two_tables_are_reset_per_load_and_one_is_not():
    """The ownership asymmetry after startup. The loader's per-load init zeroes
    the 0x28-0x2F and 0x58-0x5F tables, but not 0x30-0x57."""
    w = _life()["writers"]
    assert "0x8003a3bc" in w["zeroing_pcs"] and "0x8003a3c0" in w["zeroing_pcs"]
    # the 0x30..0x57 registrations are written but never zeroed by a loader site
    assert "0x8003bf4c" in w["populating_pcs"]
    assert "0x8003bf4c" not in w["zeroing_pcs"]


def test_pristine_startup_clear_contains_the_uncleared_per_load_table(tmp_path):
    tool = tmp_path / "e16_lifetime_guard"
    build = subprocess.run(
        ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
         str(LIFETIME_GUARD), "-o", str(tool), "-lcrypto"],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(tool)], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result["instruction_pins"] == 20
    assert result["startup_clear"]["store_pc"] == "0x8005F6A0"
    assert result["target_table"]["startup_cleared"] is True
    assert result["target_table"]["per_load_cleared"] is False


def test_lifetime_pages_do_not_restate_the_never_cleared_claim():
    pages = TABLE_PAGE.read_text() + "\n" + SYSTEM_PAGE.read_text()
    assert "this table is NEVER cleared" not in pages
    assert "Unlike its two siblings, **nothing zeroes this table**" not in pages
    assert "0x30–0x57 is never cleared" not in pages
    assert "not cleared again at the frontend-to-gameplay load boundary" in pages


def test_frontend_registrations_outlive_the_frontend():
    """38 slots populated in the frontend; 36 still hold pointers after the game
    has moved to a gameplay level."""
    a = _life()
    assert a["peak_populated_slots"] == 38
    assert a["final_populated_slots"] == 36
    assert a["truncated"] is False
    # the run really did change scene, or the question was never asked
    scenes = [s for s in a["scene_samples"] if s is not None]
    assert len(set(scenes)) > 1


def test_the_survivors_are_genuinely_dangling_not_merely_unused():
    """The distinction that makes this a finding rather than an observation: a
    chunk's marker is a u32 at its offset 0, so a surviving pointer whose target
    no longer reads back that marker points at reused memory."""
    v = _life()["survivor_validity"]
    assert v["surviving_slots"] == 36
    assert v["marker_intact"] == 0
    assert v["marker_overwritten"] == 36
    assert "GENUINELY DANGLING" in _life()["verdict"]


def test_all_survivors_belong_to_the_uncleared_table():
    s = _life()["survivors_at_end_of_run"]
    assert {x["table"] for x in s} == {"markers_0x30_0x57"}
    ptrs = [int(x["pointer"], 16) for x in s]
    assert all(0x800B0000 <= p < 0x80200000 for p in ptrs)   # the high heap


# ---- overlay ABI entry lists (analysis/phase4_e16_overlay_starts.json) ----

STARTS = ROOT / "analysis/phase4_e16_overlay_starts.json"


def _starts():
    return json.loads(STARTS.read_text())


def test_prologue_detector_reproduces_the_committed_lower_bound():
    """Cross-check that the old method was replicated faithfully before claiming
    to improve on it: it must still yield exactly the committed 27 of 42."""
    u = _starts()["union_over_the_campaign"]
    assert u["total_entry_points"] == 42
    assert u["by_prologue"] == 27


def test_return_derived_detector_raises_the_bound_and_the_pair_covers_all_42():
    """The bound was 27/42 because a prologue detector misses leaf functions.
    Deriving starts from returns finds 39, and the two together cover all 42."""
    u = _starts()["union_over_the_campaign"]
    assert u["by_return"] == 39
    assert u["by_either"] == 42
    assert len(u["only_return_found"]) == 15


def test_the_two_detectors_are_reported_as_a_bracket_not_a_replacement():
    """They err in opposite directions, which is the whole reason both are kept:
    3 entries are found ONLY by prologue matching, so the new detector does not
    subsume the old one."""
    s = _starts()
    d = s["detectors"]
    assert "UNDER-counts" in d["prologue"] and "OVER-counts" in d["return_derived"]
    assert "bracket" in d["why_both"]
    assert len(s["union_over_the_campaign"]["only_prologue_found"]) == 3


def test_overlay_count_is_20_including_one_stub():
    """The committed ABI artifact says 19 LEVEL*.BIN. There are 20 -- LEVEL00's
    is a 4-byte stub with no functions."""
    s = _starts()
    assert s["overlays_scanned"] == 20
    stub = s["per_overlay"]["LEVEL00_LEVEL.BIN"]
    assert stub["size"] == 4 and stub["returns"] == 0
    assert stub["entries_by_prologue"] == [] and stub["entries_by_return"] == []

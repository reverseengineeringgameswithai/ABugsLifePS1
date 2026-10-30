"""Phase-4 E16: campaign-wide LEVEL.RAW chunk-role census gates.

Covers analysis/phase4_e16_chunk_census.json. Chunks are classified by their
own subtype marker (u32 at decompressed offset 0), read across every
LEVEL*.RAW rather than inferred from LEVEL01 load order.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_e16_chunk_census.json"
OLD = ROOT / "analysis/level_raw_chunks.json"
EXE = ROOT / "REBUILD/files/SCUS_942.88"
MARKER20_GUARD = ROOT / "tools/phase4_e16_marker20_guard.c"
CANON = ROOT / "ObsidianVault/Canon/Memory/MEM_-_LEVEL.RAW_chunk_model.md"

GUESS_TO_FAMILY = {
    "sprite container (subtype 0x22)": {"sprite_strip_container"},
    "per-object mesh def/payload pair (obj-id keyed)": {"mesh_definition", "mesh_payload"},
}


def _art():
    return json.loads(ART.read_text())


def test_classifier_compiles_and_does_not_leave_marker_0x20_unknown(tmp_path):
    src = ROOT / "tools/phase4_e16_chunk_classify.c"
    tool = tmp_path / "chunk_classify"
    subprocess.run(["cc", "-O2", "-Werror", str(src), "-o", str(tool)], check=True)
    chunk = tmp_path / "marker20.bin"
    chunk.write_bytes((0x20).to_bytes(4, "little") + b"\0" * 12)
    run = subprocess.run([str(tool), str(chunk), "0"],
                         capture_output=True, text=True, check=True)
    result = json.loads(run.stdout)
    assert result["family"] == "sky_backdrop"
    assert result["family"] != "UNKNOWN"


def test_all_46_likely_level01_chunks_are_confirmed_by_marker():
    """E16's named next: the committed census's 46 'likely' guesses must be
    confirmed (or refuted) structurally. All 46 agree; none contradict."""
    art = _art()
    rows = {r["chunk_id"]: r for r in art["files"]["LEVEL01/LEVEL.RAW"]["rows"]}
    likely = [c for c in json.loads(OLD.read_text())["chunks"] if c["confidence"] == "likely"]
    assert len(likely) == 46
    for c in likely:
        got = rows[c["chunk_id"]]["family"]
        assert got in GUESS_TO_FAMILY[c["semantic_guess"]], (c["chunk_id"], got)


def test_structured_marker_families_are_consistent_campaign_wide():
    fam = _art()["family_histogram"]
    assert fam["sprite_strip_container"] == 228
    assert fam["mesh_definition"] == 208 and fam["mesh_payload"] == 228
    assert fam["collision_planes"] == 14 and fam["collision_sector_source"] == 14
    assert fam["seed_table"] == 17


def test_fixed_size_families():
    """Two families are byte-identical in size across every file that has
    them -- a strong structural signature."""
    art = _art()
    sizes = {"collision_sector_source": set(), "seed_table": set()}
    for v in art["files"].values():
        for r in v.get("rows", []):
            if r.get("ok") and r["family"] in sizes:
                sizes[r["family"]].add(r["size"])
    assert sizes["collision_sector_source"] == {17764}
    assert sizes["seed_table"] == {1796}


def test_mesh_pairing_law_and_its_one_exception():
    """Every mesh DEFINITION has a payload of the same object id -- never the
    reverse. Object id 11 is a payload with no definition in 16 of the 17
    mesh-bearing files."""
    art = _art()
    F = art["files"]
    mesh_files = [k for k, v in F.items() if v.get("mesh_object_ids")]
    assert len(mesh_files) == 17
    assert all(not F[k]["defs_without_payload"] for k in mesh_files)
    id11 = [k for k in mesh_files if 11 in F[k]["payloads_without_def"]]
    assert len(id11) == 16


def test_unknown_image_claim_retains_history_and_has_final_63_of_74():
    """The old all-74 and only-0x20 readings remain as history; consumers settle 63."""
    u = _art()["UNKNOWN_MARKER_ANALYSIS_2026-08-04"]
    assert u["pinned_family"]["marker"] == "0x20"
    assert u["pinned_family"]["count"] == 17
    assert len(u["pinned_family"]["three_independent_lines"]) == 3
    assert "NOT_pinned" in u and "57 chunks" in u["NOT_pinned"]["families"]
    resolved = _art()["REGISTERED_CHUNKS_RESOLVED_2026-08-04"]
    assert "46/46" in resolved["result"]
    dispositions = _art()["MARKER_SPACE_FULLY_MAPPED_2026-08-04"]["the_74_unknowns_resolved"]
    assert dispositions["0x20 sky/backdrop"] + 46 == 63
    assert dispositions["0x26 explicit arm"] == 11


def test_overfit_is_recorded_as_refuted_not_banked():
    """A permissive search 'solved' 74/74; a uniqueness check showed 0/74 are
    uniquely determined. The artifact must keep that refutation visible so the
    next pass does not repeat it."""
    u = _art()["UNKNOWN_MARKER_ANALYSIS_2026-08-04"]
    why = u["NOT_pinned"]["why"]
    assert "OVER-FIT" in why and "ZERO of the 74" in why
    hist = u["NOT_pinned"]["ambiguity_histogram"]
    assert sum(hist.values()) == 74
    assert "1 solution" not in hist          # nothing was uniquely determined
    assert "UNIQUE" in u["methodological_note"]


def test_loader_confirms_marker_at_offset_zero_and_class_split():
    """The retail loader itself reads the marker and splits the classes -- the
    census's central assumption is code-confirmed, not inferred."""
    d = _art()["LOADER_DECODE_2026-08-04"]
    assert "lw s4,0(fp)" in d["marker_is_code_confirmed"]
    assert "0x8001A1DC" in d["marker_is_code_confirmed"]
    assert "slti v0,s4,32" in d["class_split_is_code_confirmed"]
    for m in ("32", "34", "35", "36", "257", "258", "259", "260"):
        assert m in d["class_split_is_code_confirmed"]


def test_loader_pins_the_header_and_preamble_layout():
    """LoadImage(rect, base + 12 + even(u16@+8)) means pixel data begins after a
    12-byte header plus a preamble whose size is the +8 field -- turning the
    previously-guessed '768-byte palette' into a code-confirmed fact."""
    d = _art()["LOADER_DECODE_2026-08-04"]["texture_page_path"]
    assert "12 + round_down_even(u16@+8)" in d["data_pointer"]
    assert "768 is simply the value of the +8 field" in d["significance"]


def test_marker_0x20_feeds_the_sky_colour_cache():
    """RGB555 decode at +16 into 0x800771BC/C0/C4 -- the exact globals the
    committed starry-night mod patches."""
    d = _art()["LOADER_DECODE_2026-08-04"]["marker_0x20_path"]
    for a in ("0x800771BC", "0x800771C0", "0x800771C4"):
        assert a in d["addresses"]
    assert "0x84210843" in d["the_key_step"]
    assert "0x84218421" not in d["the_key_step"]
    assert "0x84218421" in d["CORRECTION_multiplier"]
    assert "inference_flagged" in d          # the 'first pixel' step is marked


def test_marker_0x20_pristine_guard_pins_multiplier_and_cache_stores(tmp_path):
    if not EXE.exists():
        import pytest
        pytest.skip("pristine SCUS_942.88 is owner-supplied")
    tool = tmp_path / "marker20_guard"
    build = subprocess.run(
        ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
         str(MARKER20_GUARD), "-o", str(tool), "-lcrypto"],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(tool), str(EXE)], cwd=ROOT,
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result["instruction_pins"] == 11
    assert result["scale_multiplier"] == "0x84210843"
    assert result["cache_addresses"] == ["0x800771BC", "0x800771C0", "0x800771C4"]


def test_marker_0x20_canon_does_not_restore_either_wrong_reading():
    page = CANON.read_text()
    assert "**What those 74 are (follow-up, same day):** images." not in page
    assert "it corroborates the committed 320×256 RGB555 loading-screen format" not in page
    assert "`0x84218421` reciprocal-multiply" not in page
    assert "True only of the `0x20` family" not in page
    assert "63/74 confirmed image resources" in page


def test_earlier_loading_screen_role_is_corrected():
    """I pinned 0x20 as a loading screen; the loader shows it is the sky/backdrop
    resource. The correction must stay visible."""
    a = _art()
    c = a["LOADER_DECODE_2026-08-04"]["CORRECTION_to_my_earlier_claim"]
    assert "ROLE was wrong" in c and "SKY/BACKDROP" in c
    assert "geometry stands" in c            # what survived is stated too
    pinned = a["UNKNOWN_MARKER_ANALYSIS_2026-08-04"]["pinned_family"]
    assert "role_corrected_2026-08-04" in pinned


def test_marker_space_is_fully_mapped_to_loader_dispositions():
    """Every previously-unclassified chunk now has a known loader disposition,
    and the three pointer-table ranges are recorded with their table bases."""
    m = _art()["MARKER_SPACE_FULLY_MAPPED_2026-08-04"]
    r = m["the_74_unknowns_resolved"]
    assert r["total"] == 74
    assert sum(v for k, v in r.items() if isinstance(v, int) and k != "total") == 74
    d = m["dispositions"]
    assert "0x8009C170" in d["0x28..0x2F"]
    assert "0x8009B4E8" in d["0x30..0x57"]
    assert "0x800A6450" in d["0x58..0x5F"]
    assert "1,796 bytes" in d["0x21..0x26"]   # the 0x23 memcpy explains the fixed size


def test_image_claim_correction_cycle_is_kept_through_final_resolution():
    """The all-images overclaim and not-images over-correction both remain visible."""
    a = _art()
    m = a["MARKER_SPACE_FULLY_MAPPED_2026-08-04"]
    assert "not evidence of an image" in m["CORRECTION_the_74_are_not_all_images"]
    assert "46 of the 74" in m["why_size_arithmetic_could_never_work"]
    assert "superseded_2026-08-04" in a["UNKNOWN_MARKER_ANALYSIS_2026-08-04"]
    final = a["REGISTERED_CHUNKS_RESOLVED_2026-08-04"]
    assert "over-corrected" in final["CORRECTION_to_my_own_correction"]
    assert "46/46" in final["result"]


def test_unknown_markers_are_enumerated_not_hidden():
    """The census surfaces a marker space larger than the committed LEVEL01
    census knew: 74 chunks carry markers outside the classified families, all
    in named files. They must be reported, not silently bucketed."""
    art = _art()
    assert len(art["unknown_markers"]) == 74
    files = {u["file"] for u in art["unknown_markers"]}
    assert files == {"LEVEL00/LEVEL.RAW", "LEVEL00/LEVEL1.RAW", "LEVEL00/LEVEL2.RAW",
                     "LEVEL00/LEVEL3.RAW", "LEVEL00/LEVEL4.RAW",
                     "LEVEL08/LEVEL1.RAW", "LEVEL09/LEVEL1.RAW"}
    markers = {u["marker"] for u in art["unknown_markers"]}
    assert "0x0020" in markers and "0x0026" in markers
    # and none of them collide with an already-classified family marker
    assert not (markers & {"0x0022", "0x0023", "0x0024", "0x0101", "0x0102", "0x0103", "0x0104"})

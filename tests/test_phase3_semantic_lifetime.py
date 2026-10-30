"""Phase-3 guard: init/reset/overlay-lifetime completes gate bullet 2.

Every owned state now has owner+width+domain (registry) + readers/writers (P1) +
init/reset/overlay-lifetime (here). The honesty this test protects: a single
transition cannot tell "reset to zero" from "was already zero", so known
session-owned fields are corroborated from the 16-stage sweep, not guessed from
one sample."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
L = json.loads((ROOT / "analysis" / "phase3_semantic_lifetime.json").read_text())
E = L["entries"]
SEM = yaml.safe_load((ROOT / "config" / "semantic_state.yaml").read_text())["entries"]
REG = {e["id"]: e for e in SEM}


def test_every_addressed_entry_has_all_three_fields():
    addressed = [e["id"] for e in SEM if isinstance(e.get("address"), int)]
    assert set(E) == set(addressed)
    for eid, v in E.items():
        assert v["overlay_lifetime"] in ("resident_rom", "resident_ram", "overlay")
        assert v["init"], eid
        assert v["reset"], eid


def test_no_written_field_is_misclassified_as_immutable_rom():
    """The audit bug: an address-threshold (<0x80090000 => ROM) wrongly labelled
    scene_id, pad words, bonus counters and allocation cursors as immutable ROM.
    They have writers. Nothing with static writers may be resident_rom."""
    import json as _j
    xr = _j.loads((ROOT / "analysis" / "phase3_xrefs.json").read_text())["entries"]
    for eid, v in E.items():
        if v["overlay_lifetime"] == "resident_rom":
            assert v.get("static_writers", 0) == 0, eid
            assert xr.get(eid, {}).get("writer_count", 0) == 0, eid
    # scene_id in particular is mutable runtime state, not ROM
    sc = E["original.current_scene_id"]
    assert sc["overlay_lifetime"] == "resident_ram"
    assert sc["reset"] != "never (immutable in ROM)"


def test_declared_mod_writers_make_private_fields_mutable_ram():
    """Static pristine xrefs cannot see MOD cave writers. The semantic registry's
    declared writers are evidence too; these three private bytes are mutable state,
    never immutable retail-image constants."""
    for eid in ("mod_private.blackberry_spawn_fast_flag",
                "mod_private.blackberry_equipped",
                "mod_private.blackberry_effective_index"):
        assert REG[eid]["writers"], eid
        v = E[eid]
        assert v["overlay_lifetime"] == "resident_ram", eid
        assert v["declared_writers"] >= 1, eid
        assert v["measured"] is False, eid
        assert "MOD" in v["derivation"], eid


def test_nothing_above_the_loaded_image_is_labeled_rom():
    """The SECOND audit bug (re-review): the writer-driven fix over-corrected. The
    static xref scan cannot see pointer-based (base+offset) stores, so pointer-
    written BSS/heap above the loaded image (actor table 0x8009FE04, camera
    0x80095358, mesh buffer 0x8012C1D0, plant slots, object-pointer list, bone bank)
    fell through to 'immutable ROM' — flatly false: those addresses are not in the
    on-disc image. NOTHING at or above 0x80082800 may be resident_rom."""
    EXE_LOAD_HI = 0x80082800
    for eid, v in E.items():
        addr = int(v["address"], 16)
        if addr >= EXE_LOAD_HI:
            assert v["overlay_lifetime"] != "resident_rom", (eid, v["address"])
    # the previously-misclassified entries are now RAM with an honest reset
    for eid in ("original.chunk31_actor_records", "original.camera_struct",
                "original.shared_mesh_vertex_buffer", "original.plant_slots"):
        v = E[eid]
        assert v["overlay_lifetime"] == "resident_ram", eid
        assert "immutable" not in v["reset"], eid


def test_rom_tables_are_derived_not_faked():
    """The remaining resident_rom entries are EXE/const tables WITHIN the loaded
    image [0x80010000, 0x80082800). Their init/reset is DERIVED from the address
    (load-time const; never reset), never a fake measurement — measured:false with a
    stated derivation. (Count dropped after the above-image entries were correctly
    reclassified to RAM.)"""
    rom = [v for v in E.values() if v["overlay_lifetime"] == "resident_rom"]
    assert len(rom) >= 12
    for v in rom:
        assert v["measured"] is False
        assert "immutable" in v["reset"] and v["derivation"]
        assert int(v["address"], 16) < 0x80082800   # in-image only


def test_ram_state_is_measured_live():
    ram = [v for v in E.values() if v["overlay_lifetime"] == "resident_ram"]
    measured = [v for v in ram if v.get("measured")]
    assert len(measured) >= 20
    # the transition really happened
    assert L["transition"]["scene"][0] != L["transition"]["scene"][1]


def test_session_owned_is_corroborated_not_guessed_from_one_sample():
    """A single transition can't distinguish reset-to-zero from already-zero. The
    known session-owned fields (lives, grain, health, permanence quota) are
    labelled carried_over ONLY when the 16-stage sweep independently says so."""
    carried = {k: v for k, v in E.items() if v["reset"] == "carried_over"}
    # lives visibly carried (9->9); anything promoted from unchanged_zero must
    # cite the sweep
    for k, v in carried.items():
        if v.get("before") == v.get("after") == 0:
            assert "transition sweep" in v.get("corroborated_by", ""), k
    assert "original.player_lives" in carried


def test_unchanged_zero_is_an_explicit_unknown_not_fake_initialization_evidence():
    """A 0->0 sample establishes neither initialization nor reset behavior. Every
    such scalar remains an explicit blocker until a nonzero->zero/reset probe exists."""
    unchanged = {k: v for k, v in E.items() if v["reset"] == "unchanged_zero"}
    assert unchanged
    assert len(unchanged) == L["reset_counts"]["unchanged_zero"]
    for eid, v in unchanged.items():
        assert v["before"] == v["after"] == 0, eid
        assert v["init"] == "unknown", eid
        assert v["blocker"]["kind"] == "insufficient_transition_evidence", eid
        assert "0->0" in v["blocker"]["observation"], eid


def test_overlay_entry_is_tied_to_its_overlay():
    ov = [v for v in E.values() if v["overlay_lifetime"] == "overlay"]
    assert ov, "training_step should be overlay-resident"
    for v in ov:
        assert "overlay" in v["init"].lower() or "swap" in v["reset"].lower()


def test_gate_bullet_2_is_complete_or_explicitly_blocked():
    """Gate bullet 2: every owned state has owner, width, domain, readers/writers,
    init, reset, overlay lifetime -- OR AN EXPLICIT BLOCKER. This computes that
    predicate across all four sources (registry + xrefs + lifetime) so closure is
    SHOWN, not asserted."""
    xr = json.loads((ROOT / "analysis" / "phase3_xrefs.json").read_text())
    reg = {e["id"]: e for e in SEM if isinstance(e.get("address"), int)}
    incomplete = []
    for eid, e in reg.items():
        has_owner = bool(e.get("owner"))
        has_width = (e.get("width") is not None
                     or e.get("kind") in ("table", "function"))
        has_domain = (bool(e.get("invariants")) or bool(e.get("domain"))
                      or e.get("kind") in ("table", "function"))
        life = E[eid]
        has_life = bool(life["overlay_lifetime"] and life["init"] and life["reset"])
        # readers/writers: present, OR the xref artifact explains why not (an
        # explicit blocker: indexed table / pointer-reached / overlay)
        xe = xr["entries"].get(eid, {})
        has_rw = xe.get("statically_referenced") or bool(xe.get("no_static_xref_because"))
        if not (has_owner and has_width and has_domain and has_life and has_rw):
            incomplete.append((eid, {"owner": has_owner, "width": has_width,
                                     "domain": has_domain, "lifetime": has_life,
                                     "readers_writers_or_blocker": has_rw}))
    assert not incomplete, f"gate bullet 2 incomplete for: {incomplete}"

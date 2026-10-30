"""Guards for the Phase-4 B06/B08 power-slot DoD item 8 ("source closure").

Item 8 asks that "matching or reviewed semantic source represents the complete
behavior, and remaining byte/layout mismatches are explicitly bounded". Byte-exact
matching is Phase 6's job and is already carried by hand-written assembly; what these
tests guard is the *reviewed semantic* half:

  1. the reconstruction exists and is labelled documentation-grade (not a build unit);
  2. it carries every constant and every enumerated site of the subsystem, so the
     "complete behavior" claim is checkable rather than asserted;
  3. its bounded residuals are stated rather than silently dropped;
  4. the "the bytes are already matched" claim cites the hash manifest, because
     asm/hand_written/ is gitignored and absent from a clean checkout;
  5. the instruction words it cites really are the pristine bytes.

Mirrors tests/test_phase4_c13_harvester.py.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import struct

import pytest


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_b06_b08_powerups.json"
CENSUS = ROOT / "analysis" / "phase4_b06_b08_census_657e.json"
CALLEE = ROOT / "analysis" / "phase4_callee_writes.json"
HEALTH_EXPECT = ROOT / "analysis" / "phase4_b06_b08_census_expected_6594.json"
SOURCE = ROOT / "src_re" / "player_power_slot_800a657e.c"
CANON = ROOT / "ObsidianVault" / "Canon" / "Systems" / "SYS_player_power_slot.md"
SYMBOLS = ROOT / "symbols" / "re_symbols.sym"
REPRO = ROOT / "tools" / "repro_inputs.sha256"
VERIFY = ROOT / "tools" / "verify_repro_inputs.py"
GITIGNORE = ROOT / ".gitignore"
WRITER_GUARD = ROOT / "tools" / "phase4_power_slot_writer_guard.c"

EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
EXE_SHA256 = "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"
EXE_BASE = 0x80010000
EXE_IMAGE_OFF = 0x800


def source_text():
    return SOURCE.read_text()


# --------------------------------------------------------------------------
# 1. the deliverable exists and is honest about what it is
# --------------------------------------------------------------------------

def test_b06_b08_source_is_labelled_documentation_grade():
    src = source_text()
    assert "Documentation-grade reconstruction" in src
    assert "This file is not a build unit; the retail bytes remain authoritative." in src
    for block in ("Evidence:", "Confirmed resident paths", "Bounded residuals:"):
        assert block in src, block
    # it must not read as a compilable build unit that merely fails to build
    assert "int main(" not in src


def test_b06_b08_source_states_the_sign_multiplex_as_the_row_model():
    src = source_text()
    assert "slot  > 0" in src and "slot  < 0" in src
    assert "consumed by TIME" in src
    assert "consumed by HITS" in src
    # the blez guard is the linchpin: no bubble is ever ticked, no timer underflows
    assert "lands EXACTLY on 0" in src


# --------------------------------------------------------------------------
# 2. every constant and every enumerated site survives in the C
# --------------------------------------------------------------------------

CONSTANTS = [
    ("G_POWER_SLOT", "0x800a657e"),
    ("TRUE_HEALTH_ADDR", "0x800a6594"),
    ("PLAYER_BLOCK_BASE", "0x800a6500"),
    ("B06_INVINCIBILITY_TICKS", "400"),
    ("B08_BUBBLE_HITS", "(-3)"),
    ("HARVESTER_TRANSIENT", "1"),
    ("STAGGER_REARM", "(-30)"),
    ("REGION_NO_DAMAGE", "5"),
    ("PLAYER_BLOCK_CLEAR_LEN", "168"),
    ("SFX_INVINCIBILITY_COLLECT", "65"),
    ("SFX_GENERIC_COLLECT", "(-3)"),
    ("SFX_CONTACT_INTERCEPTED", "14"),
    ("EFFECT_INVINCIBILITY", "57"),
    ("CTOR_INVINCIBILITY", "0x25"),
    ("CTOR_BUBBLE", "0x1f"),
    ("ACTION_INVINCIBILITY", "0x0c"),
    ("ACTION_BUBBLE", "0x2e"),
    ("G_PAIR_TABLE", "0x8007a448"),
    ("POWERFLAG_SUPER_JUMP", "0x0020"),
]


@pytest.mark.parametrize("name,value", CONSTANTS)
def test_b06_b08_source_defines_constant(name, value):
    src = source_text()
    line = next((ln for ln in src.splitlines()
                 if ln.startswith("#define " + name + " ")), None)
    assert line is not None, f"missing #define {name}"
    assert value in line, f"#define {name} does not carry {value}: {line!r}"


# every writer, reader, caller and chain hop the census enumerates
WRITERS = ["0x800588D0", "0x800589A8", "0x80048654", "0x8004A808",
           "0x80051F60", "0x8005B268", "0x80051EA0"]
READERS = ["0x80048640", "0x80049718", "0x8004A7A4", "0x8004A7E0",
           "0x80051C3C", "0x80055BC4", "0x800588B0"]
HANDLER_CALLERS = ["0x800496B0", "0x80049740", "0x80049868",
                   "0x8004B4A0", "0x80058A48", "0x8005C9F8"]
CHAIN = ["0x8005BDBC", "0x80059E44", "0x8007941C", "0x8001B570",
         "0x8005C6F0", "0x8005C744", "0x80046B68", "0x8005F7AC"]


@pytest.mark.parametrize("pc", WRITERS + READERS + HANDLER_CALLERS + CHAIN)
def test_b06_b08_source_names_enumerated_site(pc):
    assert pc in source_text(), f"{pc} is not cited in the reconstruction"


def test_b06_b08_source_records_the_s1_interception_not_the_branch():
    """The branch only ROUTES; clearing s1 is what suppresses the health write."""
    src = source_text()
    assert "only ROUTES" in src
    assert "0x8004A828" in src and "beq s1,zero" in src
    assert "damage_enabled" in src
    # 0x8004A800 is in a branch DELAY SLOT, so it retires damage on both arms
    assert "DELAY SLOT" in src
    assert "0x8004A888" in src


def test_b06_b08_source_records_the_two_place_enforcement():
    src = source_text()
    assert "CALL-SITE GATE" in src
    assert "enforced in TWO places" in src


def test_b06_b08_source_records_the_harvester_intersection_refutation():
    src = source_text()
    assert "0x8004B160" in src
    assert "REFUTED" in src or "refuted" in src
    assert "POWERUP_HARVESTER" in src


def test_b06_b08_source_records_the_renderer_sign_split():
    """0x80051C3C is gated bgez, so its body is the NEGATIVE (bubble) path."""
    src = source_text()
    assert "bubble_shell_render" in src
    assert "0x80051C44" in src and "bgez" in src
    assert "0x80078E4C" in src and "0x80078E52" in src
    # and the positive-slot consumer is the other one
    assert "invincibility_effect_id" in src
    assert "0x80055BCC" in src


# --------------------------------------------------------------------------
# 3. bounded residuals are stated, not omitted
# --------------------------------------------------------------------------

RESIDUAL_PHRASES = [
    "937",                       # same-width unresolved-base accesses
    "238",                       # unresolved indirect calls
    "0x8004DC40",                # unresolved callee destination
    "respawn_collision_reset",
    "0x8004AFB0",                # bounded but never observed firing
    "0x80079E30",                # table A semantics unresolved
    "contact-object RENDERER",
    "asm/hand_written",          # gitignored -> cite the manifest, not the tree
    "tools/repro_inputs.sha256",
    "--provision",
    "UNPROVEN",
    # Was "BOUNDED, NOT OBSERVED" for 0x8004AFB0. Retracted 2026-08-01: that site is not
    # part of this subsystem -- fp = player+4, so its store lands on player+0x82, four
    # bytes past the slot. The source must now say so rather than carry it as a residual.
    "NOT PART OF THIS SUBSYSTEM",
]


def test_b06_b08_source_does_not_model_the_knockdown_as_a_slot_writer():
    """0x8004AFB0 writes player+0x82 (fp = v1+4 at 0x8004AC70), not the power slot.

    It was modelled here as a knockdown clear of the slot and must not come back:
    a live 400-tick invincibility ticked straight through it (381 -> 380 -> 379).
    """
    src = source_text()
    assert "contact_knockdown_reaction(" not in src.replace("`contact_knockdown_reaction()`", "")
    assert "player+0x82" in src
    assert "addiu fp, v1, 4" in src or "fp = v1 + 4" in src
    assert "behavior OF THE SLOT: all 8 writers" not in src


def test_canon_does_not_reassert_the_retracted_knockdown_writer():
    canon = (ROOT / "ObsidianVault/Canon/Systems/SYS_player_power_slot.md").read_text()
    assert "**8 writers** (7 statically resolvable + 1 runtime-only):" not in canon
    assert "| `0x8004AFB0` | actor_player_contact_resolver | `:= 0`" not in canon
    assert "and on the knockdown reaction." not in canon
    assert "all 8 writers, all 7 readers" not in canon
    assert "both normal reset and exceptional knockdown clear paths" not in canon
    assert "demonstrably non-empty — `0x8004AFB0` sits in it" not in canon


@pytest.mark.skipif(not EXE.exists(), reason="pristine SCUS_942.88 is owner-supplied")
@pytest.mark.local_media
def test_power_slot_writer_guard_pins_the_pristine_writer_map(tmp_path):
    tool = tmp_path / "power_slot_writer_guard"
    build = subprocess.run(
        ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
         str(WRITER_GUARD), "-o", str(tool), "-lcrypto"],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(tool), str(EXE)], cwd=ROOT,
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result["instruction_pins"] == 27
    assert result["resolved_direct_writers"] == 7
    assert result["resolved_direct_readers"] == 7
    assert result["resolved_health_writers"] == 6
    assert result["health_damage_decrement_pc"] == "0x8004A888"
    assert result["health_alive_check_branch_pc"] == "0x8004F0E0"
    assert result["retracted_writer"] == {
        "pc": "0x8004AFB0",
        "base_delta": 4,
        "effective_player_offset": "0x82",
        "targets_power_slot": False,
    }


def test_knockdown_reachability_tool_does_not_restore_the_false_clear():
    tool = (ROOT / "tools/phase4_knockdown_reachability.py").read_text()
    assert "THE POWER SLOT CLEAR" not in tool
    assert "`0x8004AFB0` clears\nthe power slot" not in tool
    assert "v1 loaded from memory -- a runtime object pointer" not in tool
    assert "player+0x82 := 0" in tool
    probe = (ROOT / "tools/phase4_knockdown_probe.py").read_text()
    assert "*** POWER SLOT CLEARED ***" not in probe
    assert "slot clear `0x8004AFB0` IS reachable" not in probe
    assert "the knockdown clear wrote it" not in probe
    union = (ROOT / "tools/phase4_b06_b08_writer_union.py").read_text()
    assert '"0x8004afb0": "knockdown clear (static only)"' not in union
    path = json.loads((ROOT / "analysis/phase4_knockdown_path.json").read_text())
    assert "power-slot clear" not in path["_comment"]
    effect = next(row for row in path["effects"] if row["pc"] == "0x8004AFB0")
    assert "player+0x82" in effect["effect"] and "NOT the power slot" in effect["effect"]


def test_power_slot_experiment_does_not_restore_retracted_writer_claims():
    note = (ROOT / "ObsidianVault/Experiments"
            / "EXP_2026-08-01_phase4_b06_b08_power_slot.md").read_text()
    prose = " ".join(note.split())
    assert "The knockdown clear `0x8004AFB0` is **bounded, not observed**" not in prose
    assert "`0x8004AFB0` proves the class contains real slot accesses" not in prose
    assert "an applicable exceptional path that directly clears the slot" not in prose
    assert "7 writers / 7 readers" in prose


def test_damage_canon_does_not_restore_level_exit_or_four_writer_claims():
    page = (ROOT / "ObsidianVault/Canon/Functions"
            / "FUNC_8004A700_FUNC_8004A700.md").read_text()
    prose = " ".join(page.split())
    assert "`[0x800a6594]` is the **level-exit counter**" not in page
    assert "native gate at `0x8004f0e8` checks (`bltz`" not in page
    assert "only 4 instructions in the image write it at all" not in page
    assert "unique damage-side decrement among 6 statically resolved resident writers" in prose
    roles = json.loads(HEALTH_EXPECT.read_text())["writer_roles"]
    assert set(roles) == {
        "0x80046C04", "0x8004A888", "0x8005291C",
        "0x80055124", "0x80058890", "0x8005B30C",
    }


@pytest.mark.parametrize("phrase", RESIDUAL_PHRASES)
def test_b06_b08_source_states_bounded_residual(phrase):
    assert phrase in source_text(), f"residual not stated: {phrase}"


def test_b06_b08_source_bounds_its_own_scope_against_the_host_functions():
    """'Complete behavior' means the slot, not the 6,004-byte host function."""
    src = source_text()
    assert "6,004 B" in src
    assert "0x80048138..0x800498AC" in src
    assert "It does NOT reconstruct its host functions in" in src
    assert "SCOPE OF" in src


# --------------------------------------------------------------------------
# 4. the "already byte-matched" claim is anchored where it can be checked
# --------------------------------------------------------------------------

HOST_ASM = [
    "asm/hand_written/80048138_player_vertical_update.s",
    "asm/hand_written/8004a700_resident_level_transition_initiator.s",
    "asm/hand_written/8004abf4_proximity_updater.s",
    "asm/hand_written/80046b20_level_load_player_spawn_writer.s",
    "asm/hand_written/80051db4_sub_80051db4.s",
    "asm/hand_written/800586b0_contact_walker.s",
    "asm/hand_written/80059e44_contact_alloc.s",
    "asm/hand_written/8005b134_respawn_transition_state_handler.s",
    "asm/hand_written/8005bdbc_plant_spawn.s",
    "asm/hand_written/8005c6f0_seed_plant_type6_handler.s",
]


def test_b06_b08_host_functions_are_hash_pinned_outside_the_worktree():
    pinned = REPRO.read_text()
    for rel in HOST_ASM:
        assert rel in pinned, f"{rel} is not hash-pinned in tools/repro_inputs.sha256"
    assert "--provision" in VERIFY.read_text()
    # and the tree really does exclude them, which is why the manifest is the citation
    assert any(ln.strip() == "asm/" for ln in GITIGNORE.read_text().splitlines())


# --------------------------------------------------------------------------
# 5. the reconstruction agrees with the machine artifacts it cites
# --------------------------------------------------------------------------

def test_b06_b08_source_matches_the_census_artifact():
    census = json.loads(CENSUS.read_text())
    assert census["target"] == "0x800A657E"
    assert census["bytes"] == 2
    residual = census["residual"]
    # 937 before $gp was seeded (0x80081D98, 916 accesses soundly excluded) -> 882.
    # Then 882 -> 416: `unresolved` was never deduplicated by PC the way `hits` was,
    # so a block revisited during worklist convergence counted the SAME unresolved
    # instruction once per revisit. 882 was real, inflated data, not a wrong number
    # invented from nothing -- the true distinct-site count is 416. Same fix on the
    # indirect-call counter: 238 -> 149. See src_re/player_power_slot_800a657e.c.
    assert residual["unresolved_same_width_in_related_functions"] == 416
    assert residual["indirect_calls_unresolved"] == 149
    assert len(residual["related_functions"]) == 34
    # 7 statically resolvable writers. 0x8004AFB0 is NOT among them and is not
    # modelled as a slot writer at all -- see the knockdown-site correction below.
    assert {row["pc"] for row in census["writers"]} == set(WRITERS)
    assert {row["pc"] for row in census["readers"]} == set(READERS)
    assert all(row["pc"] != "0x8004AFB0"
               for row in census["writers"] + census["readers"])
    src = source_text()
    for pc in WRITERS:
        assert pc in src


def test_b06_b08_callee_write_residual_is_the_one_the_source_names():
    callee = json.loads(CALLEE.read_text())
    assert callee["target"] == "0x800A657E"
    assert callee["call_sites_total"] == 26
    # Every callee destination now resolves statically. The two that once did not were
    # an artifact of reading the first fixed-point round instead of the converged one.
    assert callee["unresolved_destination"] == []
    covering = {row["pc"]: row for row in callee["covering_target"]}
    assert set(covering) == {"0x80046B68"}
    assert covering["0x80046B68"]["dst"] == "0x800A6500"
    assert covering["0x80046B68"]["len"] == 168
    # The camera clear must stay OUT of the covering set -- it is the disjointness proof.
    not_covering = {row["pc"]: row for row in callee["not_covering"]}
    assert not_covering["0x8004DC40"]["dst"] == "0x80095358"
    assert not_covering["0x8004DC40"]["len"] == 48
    src = source_text()
    assert "0x80046B68" in src and "0x8004DC40" in src


def test_b06_b08_artifact_still_flags_item_8_and_the_row_is_partial():
    doc = json.loads(ARTIFACT.read_text())
    status = doc["ROW_STATUS"]
    assert status["B06_invincibility"] == "partial"
    assert status["B08_bubble_shield"] == "partial"
    assert status["dod_progress"]["1_original_oracle"].startswith("MET")
    shared = doc["B08_bubble_shield"]["shared_slot"]
    assert "SAME halfword" in shared
    assert "POSITIVE = invincibility" in shared and "NEGATIVE = bubble" in shared


def test_b06_b08_canon_and_symbols_back_the_reconstruction():
    canon = CANON.read_text()
    assert "0x800A657E" in canon
    assert "## Not established" in canon
    assert "sign_multiplex" not in canon  # canon is prose, the artifact holds the keys
    # Assert on ADDRESSES, not on names.
    #
    # A clean-clone verification caught this test asserting
    # "8004ABF4 actor_player_contact_resolver", a name that exists only in the
    # UNCOMMITTED working copy of symbols/re_symbols.sym -- the committed file does not
    # have it. The test passed locally and failed for everyone else, which is precisely
    # the failure mode a clean-clone gate exists to catch.
    #
    # Function NAMES churn as the census is renamed; the ADDRESSES this subsystem is
    # bound to do not. So require the address to be symbolised and report the name it
    # currently carries, rather than pinning a name that a rename can invalidate.
    symbols = SYMBOLS.read_text()
    addresses = {ln.split()[0].upper() for ln in symbols.splitlines() if ln.strip()}
    for addr, expected_hint in (("80048138", "player_vertical_update"),
                                ("800586B0", "contact_pickup_walker"),
                                ("8005B134", "respawn_transition_state_handler"),
                                ("80046B20", "level_load_player_spawn_writer"),
                                ("80051B84", "effect_render_stage"),
                                ("80055644", "player_action_effects_update"),
                                ("8004ABF4", "actor_player_contact_resolver"),
                                ("8005F7AC", "memset")):
        assert addr in addresses, (
            "%s (expected around %r) is not symbolised at all" % (addr, expected_hint))


# --------------------------------------------------------------------------
# 6. the cited instruction words really are the pristine bytes
# --------------------------------------------------------------------------

pristine = pytest.mark.skipif(
    not EXE.exists(), reason="pristine SCUS_942.88 is owner-supplied and gitignored")


def _image():
    data = EXE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == EXE_SHA256
    return data


def _word(data, va):
    off = EXE_IMAGE_OFF + (va - EXE_BASE)
    return struct.unpack_from("<I", data, off)[0]


def _bytes(data, va, n):
    off = EXE_IMAGE_OFF + (va - EXE_BASE)
    return data[off:off + n]


# every instruction word the reconstruction quotes as load-bearing
PRISTINE_WORDS = {
    # B06 grant: guard read, bgtz, unconditional store of 400
    0x800588B0: 0x87C20000,   # lh   v0, 0x0(fp)      fp = 0x800A657E
    0x800588B8: 0x1C400004,   # bgtz v0, 0x800588CC
    0x800588BC: 0x24020190,   # addiu v0, zero, 400   (branch delay slot)
    0x800588C8: 0x24020190,   # addiu v0, zero, 400   (fall-through arm)
    0x800588D0: 0xA7C20000,   # sh   v0, 0x0(fp)      delay slot of j 0x800589AC
    # B08 grant: no read of the prior value
    0x800589A0: 0x2402FFFD,   # addiu v0, zero, -3
    0x800589A8: 0xA422657E,   # sh   v0, 0x657e(at)
    # tick, with the blez guard that makes the bubble time-invariant
    0x80048640: 0x8622007E,   # lh   v0, 0x7e(s1)
    0x80048648: 0x18400003,   # blez v0, 0x80048658
    0x80048654: 0xA622007E,   # sh   v0, 0x7e(s1)
    # call-site gate
    0x80049718: 0x8622007E,   # lh   v0, 0x7e(s1)
    0x80049720: 0x14400009,   # bne  v0, zero, 0x80049748
    0x80049740: 0x0C0129C0,   # jal  0x8004A700
    # damage handler: route, sign split, stagger guard, absorb, s1, protected write
    0x8004A7A4: 0x8463657E,   # lh   v1, 0x657e(v1)
    0x8004A7B4: 0x14600008,   # bne  v1, zero, 0x8004A7D8   (ROUTES only)
    0x8004A7E0: 0x84820000,   # lh   v0, 0x0(a0)
    0x8004A7E8: 0x04410008,   # bgez v0, 0x8004A80C
    0x8004A7FC: 0x14400007,   # bne  v0, zero, 0x8004A81C   (stagger guard)
    0x8004A800: 0x00008821,   # addu s1, zero, zero         DELAY SLOT -> both arms
    0x8004A804: 0x24620001,   # addiu v0, v1, 1
    0x8004A808: 0xA4820000,   # sh   v0, 0x0(a0)            quota += 1
    0x8004A80C: 0x2402FFE2,   # addiu v0, zero, -30
    0x8004A814: 0xA4226592,   # sh   v0, 0x6592(at)         the -30 STORE
    0x8004A818: 0x00008821,   # addu s1, zero, zero
    0x8004A828: 0x12200079,   # beq  s1, zero, 0x8004AA10   the real suppressor
    0x8004A888: 0xA4236594,   # sh   v1, 0x6594(at)         protected write
    # harvester
    0x80051EA0: 0xA602FFFC,   # sh   v0, -0x4(s0)           aliased equip write
    0x80051EB0: 0xA4236590,   # sh   v1, 0x6590(at)         ori 0x80 two insns earlier
    0x80051F60: 0xA422657E,   # sh   v0, 0x657e(at)
    # resets
    0x8005B268: 0xA420657E,   # sh   zero, 0x657e(at)
    0x8004AFB0: 0xA7C0007E,   # sh   zero, 0x7e(fp)         delay slot of the jal
    0x80046B68: 0x0C017DEB,   # jal  0x8005F7AC             PsyQ memset thunk
    0x80046B6C: 0x240600A8,   # addiu a2, zero, 168
    # renderers, split by sign
    0x80051C3C: 0x84E7657E,   # lh   a3, 0x657e(a3)
    0x80051C44: 0x04E1002F,   # bgez a3, 0x80051D04         body runs iff slot < 0
    0x80055BC4: 0x8442657E,   # lh   v0, 0x657e(v0)
    0x80055BCC: 0x18400028,   # blez v0, 0x80055C70         body runs iff slot > 0
    # production chain ctor arithmetic
    0x8005C7D8: 0x00073F03,   # sra  a3, a3, 28
    0x8005C7E0: 0x24E70023,   # addiu a3, a3, 35            type 7 -> +0x23
    0x8005C728: 0x0C016791,   # jal  0x80059E44
    0x8005C72C: 0x24E7001F,   # addiu a3, a3, 31            type 6 -> +0x1F
}


@pristine
@pytest.mark.local_media
def test_b06_b08_cited_instruction_words_are_the_pristine_bytes():
    data = _image()
    wrong = {hex(va): (hex(want), hex(_word(data, va)))
             for va, want in PRISTINE_WORDS.items() if _word(data, va) != want}
    assert not wrong, wrong


@pristine
@pytest.mark.local_media
def test_b06_b08_production_chain_tables_resolve_to_the_two_grants():
    data = _image()
    pair = 0x8007A448
    # blue x1 -> type 7 / extra 0x2000 ; blue x3 -> type 6 / extra 0x0000
    assert struct.unpack_from("<HH", data, EXE_IMAGE_OFF + (pair + 4 * 4 - EXE_BASE)) \
        == (7, 0x2000)
    assert struct.unpack_from("<HH", data, EXE_IMAGE_OFF + (pair + 6 * 4 - EXE_BASE)) \
        == (6, 0x0000)
    # ctor = (extra >> 12) + 0x23 (type 7) / + 0x1F (type 6)
    assert (0x2000 >> 12) + 0x23 == 0x25
    assert (0x0000 >> 12) + 0x1F == 0x1F
    # metaB[ctor] + 0x00 is the action id
    metab = 0x8007941C
    assert struct.unpack_from(
        "<H", data, EXE_IMAGE_OFF + (metab + 0x25 * 0x14 - EXE_BASE))[0] == 0x0C
    assert struct.unpack_from(
        "<H", data, EXE_IMAGE_OFF + (metab + 0x1F * 0x14 - EXE_BASE))[0] == 0x2E
    # walker dispatch [action - 2] lands on the two grant handlers
    walker = 0x8001B570
    assert struct.unpack_from(
        "<I", data, EXE_IMAGE_OFF + (walker + (0x0C - 2) * 4 - EXE_BASE))[0] == 0x800588B0
    assert struct.unpack_from(
        "<I", data, EXE_IMAGE_OFF + (walker + (0x2E - 2) * 4 - EXE_BASE))[0] == 0x80058998


@pristine
@pytest.mark.local_media
def test_b06_b08_bubble_shell_table_is_sized_exactly_to_the_three_hit_quota():
    """0x80051C3C indexes BACKWARD from 0x80078E55 by slot*3 (slot is negative)."""
    data = _image()
    base = 0x80078E55
    assert _bytes(data, base + (-3) * 3, 3) == b"\x80\x80\x80"   # 3 hits left
    assert _bytes(data, base + (-2) * 3, 3) == b"\x60\x60\x60"   # 2 hits left
    assert _bytes(data, base + (-1) * 3, 3) == b"\x40\x40\x40"   # 1 hit  left
    # one row past the reachable quota is black, i.e. the table stops at -3
    assert _bytes(data, base + (-4) * 3, 3) == b"\x00\x00\x00"


@pristine
@pytest.mark.local_media
def test_b06_b08_table_a_row_for_the_bubble_stack_arg_is_all_zeros():
    """The residual the reconstruction records: table A is not indexed as assumed."""
    data = _image()
    assert _bytes(data, 0x80079E30 + 3 * 0x14, 0x14) == bytes(0x14)


@pristine
@pytest.mark.local_media
def test_b06_b08_damage_handler_has_exactly_six_resident_callers():
    data = _image()
    found = []
    total = (len(data) - EXE_IMAGE_OFF) // 4
    for i in range(total):
        va = EXE_BASE + i * 4
        word = struct.unpack_from("<I", data, EXE_IMAGE_OFF + i * 4)[0]
        if word >> 26 in (2, 3):
            target = ((va + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
            if target == 0x8004A700:
                found.append(f"0x{va:08X}")
    assert found == HANDLER_CALLERS


# ---------------------------------------------------------------------------
# Census soundness: the straddling-store hole.
#
# The census hit-test used to be `if ea in targets`, which only catches an access
# that STARTS on a target byte. The slot 0x800A657E is at offset 0x7E -- deliberately
# NOT word-aligned -- so an aligned word store at 0x800A657C writes bytes 7C..7F and
# clobbers it while starting two bytes below. That access was invisible.
#
# Censusing the resident image found ZERO such stores, so the hole is empty for this
# target -- but "empty" was only worth stating once the detector was known to work.
# These tests exercise the overlap logic on a synthetic image, because the real image
# never triggers it.
# ---------------------------------------------------------------------------

SLOT_ADDR = 0x800A657E


class _FakeImage:
    """Minimal stand-in for census_address.Image over a hand-built instruction list.

    `funcs`, when given, is a list of (address, name, size) -- use it to build a
    multi-function synthetic image (e.g. a dispatcher plus a callee) so a jalr/jr
    resolution test can isolate one function's body from another's.
    """

    def __init__(self, words, base=0x80000000, funcs=None):
        self.base = base
        self.text = b"".join(struct.pack("<I", w) for w in words)
        self.end = base + len(self.text)
        self.funcs = funcs or [(base, "synthetic", len(self.text))]
        self.starts = [f[0] for f in self.funcs]

    def word(self, va):
        return struct.unpack_from("<I", self.text, va - self.base)[0]

    def owner(self, va):
        import bisect
        i = bisect.bisect_right(self.starts, va) - 1
        return self.funcs[i] if i >= 0 else self.funcs[0]

    def extent(self, start):
        import bisect
        i = bisect.bisect_left(self.starts, start)
        a, _, size = self.funcs[i]
        if size:
            return a + size
        return self.funcs[i + 1][0] if i + 1 < len(self.funcs) else self.end

    def is_function_start(self, va):
        import bisect
        i = bisect.bisect_left(self.starts, va)
        return i < len(self.starts) and self.starts[i] == va


def _lui(rt, imm):
    return (0x0F << 26) | (rt << 16) | (imm & 0xFFFF)


def _addiu(rt, rs, imm):
    return (0x09 << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def _store(op, rt, rs, off):
    return (op << 26) | (rs << 21) | (rt << 16) | (off & 0xFFFF)


def _census(words, target=SLOT_ADDR, width=2):
    sys.path.insert(0, str(ROOT / "tools"))
    import census_address as ca
    img = _FakeImage(words)
    hits, _unresolved, _indirect = ca.analyse(
        img, set(range(target, target + width)), gp_value=None)
    return hits


def test_census_catches_a_word_store_that_straddles_the_slot():
    """sw at 0x800A657C covers 7C..7F -- it clobbers the slot without starting on it."""
    words = [_lui(1, 0x800A), _addiu(1, 1, 0x657C),
             _store(0x2B, 2, 1, 0), 0x03E00008, 0]
    hits = _census(words)
    assert len(hits) == 1, f"straddling word store was missed: {hits}"
    assert hits[0]["straddles"] is True
    assert hits[0]["address"] == "0x800A657C"
    assert "0x800A657E" in hits[0]["covers"]


def test_census_catches_a_halfword_store_landing_exactly_on_the_slot():
    """The ordinary case must keep working, and must NOT be flagged as straddling."""
    words = [_lui(1, 0x800A), _addiu(1, 1, 0x657E),
             _store(0x29, 2, 1, 0), 0x03E00008, 0]
    hits = _census(words)
    assert len(hits) == 1
    assert hits[0]["straddles"] is False
    assert hits[0]["address"] == "0x800A657E"


def test_census_does_not_flag_an_adjacent_word_store_that_stops_short():
    """sw at 0x800A6578 covers 78..7B and must NOT be reported -- no false positives."""
    words = [_lui(1, 0x800A), _addiu(1, 1, 0x6578),
             _store(0x2B, 2, 1, 0), 0x03E00008, 0]
    assert _census(words) == []


# ---------------------------------------------------------------------------
# Indirect-call (jalr) resolution.
#
# The census used to treat EVERY jalr as an unresolved indirect call, even when the
# jump-target register's value was already known to the value analysis -- silently
# discarding argument propagation through resolved indirect calls. The real image
# happens to resolve 0 of them (every jalr target in this game's code turns out to
# derive from a value the analysis genuinely cannot pin down), so these paths are
# exercised only on a synthetic image built for the purpose.
# ---------------------------------------------------------------------------

def _lw(rt, rs, off):
    return (0x23 << 26) | (rs << 21) | (rt << 16) | (off & 0xFFFF)


def _jalr(rs):
    return (rs << 21) | 0x09


def _jr(rs):
    return (rs << 21) | 0x08


T0, T1, A0, RA = 8, 9, 4, 31


def test_census_resolves_a_jalr_through_a_static_dispatch_table_and_propagates_a0():
    """Dispatcher loads a0 = the slot address, then calls through a table entry read
    from the pristine image. The callee stores via a0. This must show up as a hit --
    it only does if BOTH the jalr target AND the argument propagation now work."""
    dispatcher = [
        _lui(A0, 0x800A), _addiu(A0, A0, 0x657E),   # a0 = 0x800A657E (the slot)
        _lui(T1, 0x8000), _addiu(T1, T1, 0x1C),     # t1 = &data word (index 7)
        _lw(T0, T1, 0),                             # t0 = table[0] = callee address
        _jalr(T0), 0,                                # jalr t0 ; delay slot: nop
    ]
    data_word = [0]  # placeholder; patched below once the callee address is known
    callee = [
        _store(0x29, 0, A0, 0),                     # sh zero, 0(a0)
        _jr(RA), 0,
    ]
    base = 0x80000000
    words = dispatcher + data_word + callee
    callee_addr = base + len(dispatcher) * 4 + len(data_word) * 4
    words[len(dispatcher)] = callee_addr             # bake the callee's real address in

    sys.path.insert(0, str(ROOT / "tools"))
    import census_address as ca
    funcs = [(base, "dispatcher", len(dispatcher) * 4),
             (callee_addr, "callee", len(callee) * 4)]
    img = _FakeImage(words, base=base, funcs=funcs)
    hits, unresolved, indirect = ca.analyse(
        img, {SLOT_ADDR, SLOT_ADDR + 1}, gp_value=None)

    assert indirect == 0, "the jalr must resolve, not count as an unresolved indirect call"
    assert len(hits) == 1, f"a0 propagation through the resolved call failed: {hits}"
    assert hits[0]["function"] == "callee"
    assert hits[0]["address"] == "0x800A657E"


def test_census_does_not_resolve_a_jalr_through_a_runtime_computed_pointer():
    """A jalr through a register whose value is genuinely unknown (loaded from an
    address OUTSIDE the static image, i.e. a runtime object, not compile-time data)
    must still count as unresolved -- the new path is scoped to static tables only."""
    base = 0x80000000
    dispatcher = [
        _lui(T1, 0x8010), _addiu(T1, T1, 0),        # t1 = 0x80100000, OUTSIDE the image
        _lw(T0, T1, 0),                             # t0 = TOP -- runtime data, not baked-in
        _jalr(T0), 0,
    ]
    words = dispatcher
    funcs = [(base, "dispatcher", len(dispatcher) * 4)]
    sys.path.insert(0, str(ROOT / "tools"))
    import census_address as ca
    img = _FakeImage(words, base=base, funcs=funcs)
    hits, unresolved, indirect = ca.analyse(
        img, {SLOT_ADDR, SLOT_ADDR + 1}, gp_value=None)
    assert indirect == 1, "an out-of-image pointer load must NOT be trusted as a table read"


# ---------------------------------------------------------------------------
# Region-provenance cross-validation artifact (tools/region_provenance.c, run via
# tools/phase4_region_provenance_report.py). Pins the reconciled result, not just the
# tool's own self-report -- if a future change to either implementation makes them
# disagree, `validation.reconciles_exactly` catches it before the headline number is
# trusted again.
# ---------------------------------------------------------------------------

REGION_ARTIFACT = ROOT / "analysis" / "phase4_region_provenance.json"


@pytest.mark.skipif(not REGION_ARTIFACT.exists(), reason="region-provenance artifact not generated")
def test_b06_b08_region_provenance_reconciles_with_zero_drift():
    doc = json.loads(REGION_ARTIFACT.read_text())
    v = doc["validation"]
    assert v["hit_set_matches_python"] is True
    assert v["python_hits"] == v["c_hits"]
    assert v["lost_sites (C dropped, MUST be empty)"] == []
    # The one catastrophic failure mode: a C exclusion claiming a site that Python
    # KNOWS is a real slot access. Must be empty, always.
    assert v["c_exclusions_colliding_with_python_hits (MUST be empty)"] == []
    # COMBINED-PROVER accounting (2026-08-01g): C's region merges can absorb a
    # constant pointer into a walking region, leaving a site C-open that Python's
    # exact constants prove disjoint. Such sites are benign ONLY when verified
    # (absent from Python's hits AND its full any-width unresolved list) -- anything
    # else is unexplained and fails.
    assert v["c_open_unexplained (MUST be empty)"] == []
    assert v["reconciles_exactly"] is True

    r = doc["result"]
    assert r["baseline_residual"] == 416
    # History of the excluded count, each step cross-validated:
    #   35: block-local sll/addu regions (alignment + negative-index)
    #   63: shift-hint propagated across block boundaries
    #   72: walking-pointer arithmetic-progression regions
    #  165: (2026-08-01g) loop-carried region merges fixed properly -- same-residue-
    #       class REGION/REGION merge (previously collapsed to TOP the moment the loop
    #       closed, killing the walking region it had just built) + CONST absorbed
    #       into a compatible REGION + va=0 anchor CANONICALIZATION (0x80000000 +
    #       anchor mod S) so reverse-walking pointers converge instead of churning the
    #       worklist into the visit cap (the churn was silently truncating final-round
    #       scans -- observed as a 149->143 indirect-count drop, now warned about and
    #       gone). Also fixed in the same pass: the region tier's straddle-window
    #       soundness hole (it tested only A == target_lo, the same start-address-only
    #       bug fixed in census_address.py's hit test earlier; now the full overlap
    #       window [want-(w-1), want+tw-1] is tested). ZERO previously-committed
    #       exclusions were invalidated by the fix -- verified by diffing against the
    #       committed artifact. Hand-verified survivor: 0x8005A360 in
    #       berry_projectile_update, canonical anchor 0x80000022 stride 56 (same
    #       residue class as the contact array: 0x800B0D3A - 0x80000022 = 12933*56
    #       exactly), window {681307,681308,681309} contains no multiple of 56.
    assert r["excluded_by_region_provenance"] == 224   # was 165; +59 mask bounds
    assert r["excluded_alignment"] == 159
    assert r["excluded_negative_index"] == 6
    # 2026-08-04: was 251. A MASK is an unconditional index bound -- `andi rt,rs,M`
    # clamps the result to [0, M] with no branch and no comparison -- and wiring that
    # into the analyser (ported from tools/affine_bound_recovery.c) discharged 59 more
    # in-scope sites. Hand-verified example: 0x800470F8 reads a 4096-entry stride-2
    # trig table at 0x80074970 whose index is masked by `andi 0x0fff`, so its reachable
    # window ends at 0x8007696E and the power slot is 101,895 entries away. The
    # reconciliation harness still reports hit-set-matches-python and CLEAN, so no
    # known-real access was excluded.
    assert r["still_open_after_region_provenance"] == 192

    # TIER 3 (loop-bound extraction) still finds ZERO exclusions inside THIS target's
    # 34-function scope -- a real, hand-verified negative result, not a bug. Pinned
    # because it's shared infrastructure: a regression in the bound_hint machinery
    # should be caught even though it has no effect on B06/B08's own number.
    # (Whole-image count rose 27 -> 75 with the merge upgrades: more regions now
    # survive long enough to carry a bound.) Hand-verified example: 0x800370A4 in
    # collision_probe_candidate_pass, where `slti v0,t3,48 / beq v0,zero,exit` at
    # 0x80036E98 genuinely gates the same t3 that later forms `sll a0,t3,3` -- bound
    # 48 and stride 8 both match the disassembly exactly.
    assert r["excluded_out_of_bound"] == 59            # was 0; all from andi masks
    # 2026-08-04, two changes on the same day, in opposite directions:
    #   75 -> 40  TIER 3 was proven UNSOUND (it asserted a bound from the mere
    #             existence of a comparison and propagated it to the branch where the
    #             comparison FAILED); 35 wrong exclusions were removed. Counterexample:
    #             tests/test_region_provenance_bound_soundness.py.
    #   40 -> 167 a MASK is an unconditional bound, and wiring `andi` in recovered far
    #             more than the unsound tier ever produced -- soundly this time.
    # 108 of the 167 fall outside this target's scope; the other 59 are the in-scope
    # exclusions that moved this row from 251 to 192.
    assert doc["whole_image_excluded_out_of_bound_total"] == 167
    assert doc["whole_image_out_of_bound_exclusions_not_in_this_scope"] == 108

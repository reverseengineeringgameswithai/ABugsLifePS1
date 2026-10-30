---
kind: system
id: SYS_cinematic_camera
created: 2026-08-04
updated: 2026-08-05
status: live_confirmed
confidence: confirmed
source_state: original_game
functions: [cinematic_camera_start, cinematic_camera_start_polar, camera_source_selector, setpiece_actor_update, hud_draw, draw_mirrored_fullscreen_quads]
memory: [0x80090BC0, 0x80090BEC, 0x80090BEE, 0x800A6590, 0x8009EC50]
tables: []
constants: []
evidence: [EXP_2026-08-04_phase4_d16_f03_thumper_council_chamber]
src_paths: []
patch_policy: safe_to_read
---

# SYS_cinematic_camera — the setpiece camera, its flags, and cutscene suppression

## Purpose

The camera the game switches to for scripted moments — telescope hints, the bird flyby, boss-defeat
sequences. It reuses one global block, and its **flags field `0x80090BEE` has repeatedly been
mistaken for a per-boss state variable**. It is not one.

## The block — `0x80090BC0`

A single shared setpiece-camera record. The two start functions write it field by field:

| offset | address | notes |
|---|---|---|
| +0x00…+0x20 | `0x80090BC0`…`0x80090BE0` | position / target / derived vectors |
| +0x24 | `0x80090BE4` | halfword, zeroed at start |
| +0x26 | `0x80090BE6` | halfword, angle from `0x80060AE4` (or arg) |
| +0x28 | `0x80090BE8` | halfword, zeroed at start |
| **+0x2C** | **`0x80090BEC`** | **phase** — drives the state machine below |
| **+0x2E** | **`0x80090BEE`** | **flags** — caller-supplied at start |

This is the same block [[EXP_2026-08-03_phase4_c14_telescope]] reaches through (index →
`0x80096DC8` → waypoint record → `0x80090BC0`) and the one D17's bird setpiece uses.

## Starting a cinematic

Two entry points, both taking the flags as an **argument**:

- **`cinematic_camera_start`** `0x8004D9E8` — flags = arg7 (`0x8004DA7C`), phase := 2 (`0x8004DA74`).
- **`cinematic_camera_start_polar`** `0x8004DA94` — flags = arg8 (`0x8004DB44`), phase := 2
  (`0x8004DB50`). Computes position from an angle via the table at `0x80074970`.

`0x8004D9E8` has exactly one resident caller — the telescope setpiece path at `0x8004D730`, which
passes **flags = 2** unconditionally (`0x8004D6F4`). `0x8004DA94` has **13** callers, all in level
overlays, passing 2 or 3.

> **`0x80090BEE = 2` is therefore not a state code and not boss-specific.** It is the flags value a
> caller passes when starting a cinematic. Any claim of the form *"event X sets `0x80090BEE` to 2"*
> is really *"event X starts a cinematic camera with bit 0x02 set"*.

## The selector — `camera_source_selector` `0x8004EA8C`

⚠️ The function census auto-names this `enemy_ai_dispatcher`. **That name is wrong.** It switches on
the phase `0x80090BEC`:

| phase | action |
|---|---|
| 2 | `four_byte_store(0,0,0,16)`; phase := 1; if flags & 2 → `0x800A6590` \|= 0x04 |
| 1 | wait for `[0x80082388] == 0`; `four_byte_store(128,128,128,16)`; flags \|= 0x01; phase := 0 |
| 3 | wait for `[0x80082388] == 0`; `four_byte_store(128,128,128,16)`; phase := 0; flags &= ~0x01; if flags & 2 → `0x800A6590` &= ~0x04 |
| 4 | `four_byte_store(0,0,0,16)`; phase := 3 |

Tail (every frame, `0x8004EBEC`): if `flags & 1`, run `setpiece_actor_update(0x80090BC0)` and take
the camera parameters from the setpiece block; otherwise take them from the ordinary follow camera
`0x80095358` ([[SYS_camera]]). Either way the six outputs land at `0x8009EC50`.

## The flags

- **bit 0x01 — cinematic camera ACTIVE.** Selects the camera source (above), and makes
  `gameplay_state_machine` swap the HUD: at `0x8004F3D0` and `0x8004F6DC` it skips
  `jal 0x800526F4` (`hud_draw`) and calls `jal 0x80053638`
  (`draw_mirrored_fullscreen_quads`) instead — **cinematic letterboxing**, not a boss health bar.
- **bit 0x02 — hold `0x800A6590` bit 0x04 for the duration.** ORed in when the cinematic starts,
  cleared when it ends.

Complete access census (pristine EXE + all 21 overlay blobs, two independent methods, compared as
sets): **11 accesses, 10 resident + `LEVEL02/LEVEL1.BIN` `0x800B4560`.** All are `lhu`/`sh`
(halfword). Blind spot, stated not claimed against: an access through a pointer loaded from memory.

## `0x800A6590` bit 0x04 is a SUPPRESSION gate, not a power-up

It is **not** a member of the power set in [[SYS_player_power_slot]] (0x02 invincibility, 0x08
bubble, 0x20 super-jump). All five readers share one shape — **set → branch past the body**:

| reader | enclosing function | what it skips |
|---|---|---|
| `0x8004EED0` | `gameplay_state_machine` | jumps to the branch that masks the player action word `0x80082488` down to `0x309` |
| `0x80050C84` | `contact_pickup_sfx` | pickup SFX |
| `0x80051138` | `ambient_sfx_sequence_update` | ambient SFX sequencing |
| `0x80054F38` | `sfx_nearest_pickup_f_glue` | nearest-pickup SFX |
| `0x80056550` | `actor_skinned_update` | part of the skinned-actor update |

It never enables anything. Read it as *"a cutscene is running — suppress player input and ambient
audio."*

## Traced facts (Interpreter movie, write-watches — 2026-08-04)

- **Case 3 (the exit path) never fires in the Council Chamber.** Across 4060 frames the flags word
  is written exactly three times: BIOS 0 → `2` (camera start `0x8004DB44`) → `3` (case 1
  `0x8004EB1C`). The level ends with the cinematic active and `0x800A6590` bit 0x04 still set.
  Case 3 therefore belongs to cinematics that **return to gameplay** (the telescope path), not to
  level-ending ones.
- **`0x80082388`** — the value cases 1 and 3 wait on — is the **transition countdown** owned by
  `contact_cursor_transition_reset` `0x80054AD4`, the function immediately after `four_byte_store`
  `0x80054AAC`. 201 writes, all from that subsystem.
- **`four_byte_store` `0x80054AAC`** writes `0x80082362`, `0x8008248A`, `0x8008241E`, `0x8008248B`.
  The first three are set-and-hold; the fourth is rewritten thousands of times per run. Consistent
  with tint/fade parameters plus a duration, but the consumer is untraced — do not cite as proven.
- ⚠️ **`0x80090BF2` / `0x80090BF6` are NOT part of this block's meaningful state, and are not
  Thumper's.** A legacy note called them "fight phase/attack counters". `0x80090BF6` is written
  **only by the BIOS** (bulk zeroing at load). `0x80090BF2` is written 38× by
  `gameplay_effect_spawner` `0x8005CD2C`, cycling 0/1/1/2 on a ~48-frame period throughout play —
  nothing to do with the boss. Note `0x80090BF2` has **zero** absolute stores in any image: it is
  written through a pointer, so a static census alone cannot see it.

## Identifying which overlay is resident — provenance plus an independent writer

Region A blobs **mutate their own first bytes at runtime**, so a raw hash of
`0x800B39A0` can identify the blob shortly after load and then read as
unrecognised mid-level. Use `memory.getResidency` for the complete Region-A
buffer before resolving the writer. Preserve its source file/offset, runtime
base/size, source and resident hashes, `sourceMatchesResident`, load generation,
timestamp, frame, and cycle; re-query immediately before the breakpoint or
trace. Re-resolve if the generation changes, and record any hash-only change as
resident-byte divergence under the same tracked load.

An exact recorded CD-DMA provenance entry can retain the overlay's source
identity after self-modification even when `sourceMatchesResident:false`.
Without exact provenance, a mismatch is unresolved rather than permission to
guess from familiar instructions. The residency ledger and generation counter
are runtime-only and reset across state/reset/media boundaries; they do not
survive a save state.

Keep the **writer PC** as an independent behavioral control: a write to
`0x800823A0` from `0x800B4190` can only occur if the resident blob whose
`0x800B4190` is `sh v0,0x23a0(at)` is executing. A strong replay records both the
residency identity/generation and this instruction-attributed hit. If the trace
asserts memory at that hit, arm `execTrace` with bounded `capture_memory` so the
value is sampled before the instruction rather than read later.

## Related

- [[SYS_camera]] — the ordinary follow camera and the world→view transform.
- [[EXP_2026-08-03_phase4_c14_telescope]] — the telescope path into this block.
- [[Thumper_boss_fight]] — the Council Chamber defeat starts one of these, which is where the
  "defeat flag" misreading came from.
- [[EXP_2026-08-04_phase4_d16_f03_thumper_council_chamber]] — derivation, census, and live run.

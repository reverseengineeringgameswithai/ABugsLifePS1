---
kind: system
id: SYS_record_layouts_and_lifetimes
name: Record layouts, ownership and lifetimes (typed without erasing unknowns)
status: live_confirmed
confidence: confirmed
source_state: original_game
memory:
  - MEM_800A6500
  - MEM_800B0D18
evidence:
  - EXP_2026-07-12_phase3_architecture_maps
  - analysis/phase3_record_types.json
  - analysis/phase3_record_probe.json
  - analysis/phase3_unknown_fields.json
  - analysis/phase3_transition_reset.json
  - analysis/phase3_camera_record.json
  - analysis/phase3_render_descriptors.json
  - analysis/phase3_sfx_interface.json
  - analysis/phase3_fn_ptr_fields.json
  - analysis/phase3_xrefs.json
  - analysis/phase3_semantic_lifetime.json
src_paths:
  - config/record_types.yaml
  - tools/phase3_record_types.py
---

# SYS_record_layouts_and_lifetimes

Phase-3 WP5/WP6. Eight record views cover all twelve required families under one rule: **typing must
not erase ignorance.** Every byte of every record is either a declared field or
an explicit **UNKNOWN span**, so the amount we do not know is a visible number
that can only shrink by adding evidence. Source of truth:
`config/record_types.yaml`; the layout validator refuses overlaps, misalignment,
out-of-extent fields, and any record missing a lifetime statement.

## Byte accounting (current)

| Record | Base | Size | Instances | Typed |
|---|---|---|---|---|
| `player_block` | `0x800A6500` | `0xB0` | 1 | 71/176 B (40.3%) |
| `contact_record` | `0x800B0D18` | `0x38` | 64 | 31/56 B (55.4%) |
| `actor_record` | `0x8009FE04` | `0x84` | 40 | 38/132 B (28.8%) |
| `plant_slot` | `0x80090BF0` | `0x30` | 20 | 3/48 B (6.2%) |
| `camera_record` | `0x80095358` | `0x60` | 1 | 24/96 B (25.0%) |
| `render_descriptor_pointer_entry` | `0x80096B98` | `0x04` | 50 | 4/4 B (100%) |
| `sfx_voice_slot` | `0x80089860` | `0x08` | 8 | 6/8 B (75.0%) |
| `frontend_progress_record` | `0x80082444` | `0x04` | 1 | 4/4 B (100%) |

**181/524 bytes typed (34.5%).** The remaining 65.5% is *named as unknown*, not
hidden. A layout-validator catch worth keeping: `berries_in_flight` at `+0x96`
is **u8, not u16** — a u16 there would silently swallow `equipped_berry` at
`+0x97`.

## Lifetimes (WP6)

- **`player_block`** — not pooled; resident for the session, re-initialized at
  scene load and at respawn (hp := 4 at the spawn point, lives − 1).
- **`contact_record`** — **pooled**, and the pool is dangerous. `contact_alloc`
  (`0x80059E44`) is a round-robin **free-slot search with no full-array escape**:
  with every slot occupied it never returns. The cursor `0x8008234C` wraps at
  `0x40` and measures allocation *churn* — it is **not** overwrite-oldest.
  **Retirement is by TTL expiry** (`+0x22` counts down to 0) — see below.
- **`actor_record`** — loaded **at scene load** from LEVEL.RAW chunk-31 into a
  *fixed* table; records are not reallocated during play. Enemies also appear in
  the live pointer table `0x80090748`, which is **compacted on removal** — so a
  live-table *index* is not a stable identity; the record *address* is.
- **`plant_slot`** — pooled behind a cursor (`0x800822B8`, wraps at `0x14`, skips
  occupied). Created 20–120 frames after the crack input, torn down 40–170 frames
  after an uproot; the seed record is conserved across the cycle.
- **`camera_record`** — a derived per-frame output; the follow producer owns both
  triples and overwrites direct edits.
- **`render_descriptor_pointer_entry`** — a fixed 50-entry resident pointer table;
  pointers are stable across strict-pristine post-load anchors, while five target-byte
  offsets are scene-dependent. Seven bytes are invariant. The snapshot census does
  not identify their writer.
- **`sfx_voice_slot`** — an eight-slot scheduler pool; `voice_id == -1` denotes a
  free slot and the voice manager owns retirement.
- **`frontend_progress_record`** — resident frontend state with an explicit
  three-part blocker for the still-unmeasured create/save/load/delete lifecycle.
  That blocker is a bounded WP6 result, not an invented reset law.

## Occupancy — measured with the game's own predicates

⚠️ **A dead slot keeps RESIDUE.** "Has non-zero bytes" is *not* occupancy, and
using it produces a false reading of 64/64 contact slots — which would contradict
the capacity hang (the game would be hanging constantly). Occupancy must use the
game's predicates, which are *two different tests*:

- **live / walker gate** (`FUNC_800586B0`): `lifetime_ttl(+0x22) > 0 AND flags(+0x33) & 0x02`
- **allocator-occupied** (`contact_alloc`'s skip test): `flags & 0x80 AND lifetime_ttl != 0`

Sampled across 42 centrally declared, hash-pinned strict-pristine anchors. The former
Training save is excluded because its embedded media path identifies ALLMODS; a
from-boot pristine replay supplies the replacement Training anchor.

| Record | live | allocator-occupied peak | headroom |
|---|---|---|---|
| `contact_record` | 0–2 | **4 / 64** | **60** |
| `plant_slot` | 0–12 | 12 / 20 | 8 |
| `actor_record` | 0–40 | 40 / 40 | 0 (fixed table — capacity *is* the roster) |

**Conclusion for modding:** pristine play never comes close to the contact-pool
capacity (peak 4 of 64). The allocator hang is therefore a **mod-introduced
risk**, not a latent retail bug — but it stays a hard constraint: *never let a mod
hold all 64 contact slots.*

## The integrators (drained from the unknown queue, `tools/phase3_unknown_fields.py`)

Found by exact-match hypothesis testing: capture the whole record every frame
while the object moves, then promote only fields that **equal the per-tick
position delta**. The berry's known gravity is the built-in control — the tool
rediscovered `128/frame²` from the raw bytes, so its verdicts are trustworthy.

| Record | velocity X | velocity Y | velocity Z |
|---|---|---|---|
| `player_block` | `+0x2C` s32 | `+0x30` s32 | `+0x34` s32 |
| `contact_record` | `+0x0C` s32 | `+0x10` s32 | `+0x14` s32 |
| `actor_record` | `+0x1C` s32 | `+0x20` s32 (CONFIRMED 2026-08-02/03, see below) | `+0x24` s32 |

The retained Level01 actor sample confirms `+0x1C` as X velocity and `+0x24` as Z
velocity over 40 captured frames (19 moved-frame deltas; Z is clamped on seven).
It does **not** reproduce the former claim that all actors lack a stored Y velocity:
the artifact retains promoted matches but not its rejected Y-candidate table, and it
used one actor/anchor rather than the advertised 42 anchors and 92 ticks.

**`+0x20` is now CONFIRMED `velocity_y`** (Phase 4 D02_mover_vm, 2026-08-02/03) — but
not via the exact-frame-delta method above, which correctly does NOT work for this
field: collision/update handlers consume, cap, and clear the value mid-tick, so it
only matches the final frame-boundary Y displacement 4.3% of the time (6 retained
capsules, 2895 records) despite genuinely being velocity. A dedicated Interpreter
movie (recording Flik throwing a mine at a spider) with 40 per-actor-record
read/write watches on `+0x20` classified all 1,991 accesses (1,178 reads, 813
writes) across 8 writer PCs with zero unclassified: two gravity integrators
(`+0x100`/frame toward a `+0x1000` cap, at `0x8004BF14..38` and `0x8004CF34..50`),
direct Y-position integration at both sites, an airborne launch impulse (`-0xD00`
or `-0xB60`) at `0x80049E00`, a near-zero settle-clear, and a collision-path clear
at `0x8004D024` (a MIPS branch delay slot — executes for either branch outcome, not
conditional on it). This closes the "bounded residual" this page previously
flagged: the earlier warning about not naming it from stride symmetry was correct
caution, but full writer/reader instruction attribution (not symmetry) now confirms
it. Full detail: `analysis/phase4_d02_actor20_runtime.json`,
`analysis/phase4_d02_actor20_deep_audit.json`,
`ObsidianVault/Experiments/EXP_2026-08-02_phase4_d02_actor20.md`.

Plus `player +0x38` = horizontal speed (tracks `hypot(vx, vz)` to ~1 unit), and
`contact +0x18` = **`gravity_per_tick` = 128** — the per-record store of the
known fall law.

### Two corrections this forced

1. **`player +0x30` is `velocity_y`, not `knockback_velocity`.** It exactly equals
   the per-tick Y delta while jumping. The on-hit knockback writes `-1024` there
   *because knockback is a vertical impulse* — the old name described one writer
   and mistook it for the field's meaning.
2. **`contact +0x22` is `lifetime_ttl`, not `active_type`.** It is a **countdown**
   (e.g. 172, 171, … 0 at 30 Hz), and the slot is **retired at 0**. So the walker
   gate's `> 0` means *"TTL not expired"*, not *"has a type"*.

### Why the pool never fills (WP6, now explained)

**Contacts free themselves.** Retirement is by TTL expiry, not by an explicit
release — which is exactly why pristine play peaks at 4 of 64 slots and never
meets the allocator's no-escape hang. A mod that *refreshes* TTLs, or holds slots
open, removes the very mechanism that keeps the pool drained.

### Method notes worth keeping

- The game integrates on **alternate frames** (30 Hz logic on 60 Hz frames); a
  zero delta is a no-op tick, not counter-evidence.
- A velocity is a **move proposal**: the integrator may **clamp** the position
  (collision/ground) while the velocity persists, so demanding equality on *every*
  frame rejects real fields. Require a long consecutive exact run instead.
- Velocities differ in **write order**: the player's is written *after* the move
  it caused; the berry's is *pre-integrated* (gravity applied first, so at tick t
  it already holds tick t+1's delta).
- **Never accept a match on a zero delta** — while jumping in place `dx == 0` and
  half the record is zero, so `0 == 0` will "prove" every field.

## The SFX interface — `sfx_dispatch` `0x80050994`

A callable "play a sound" boundary, characterised by **calling it** rather than
reading it: for each candidate id, invoke it on a fresh pristine anchor and ask the
**SPU** whether a voice actually keyed on.

- **`a0` = the sfx id, and it is SIGNED** — both seed-impact arms pass `a0 = -4`.
- Swept `-24..48`: **27 ids play**, each starting a **distinct sample** (no aliases
  in that range).

⚠️ **`v0` is NOT a success flag.** It reads `0x4` for every id that plays **and for
36 ids that stay silent**. *"It returned 4, so it worked"* is exactly the wrong
inference — only the SPU proves a sound started. A mod must not branch on the
return value.

## ⚠️ Render descriptors: stable pointers, scene-dependent bytes

`object_pointer_list` `0x80096B98` maps **kind (0..49) → a 0xC-byte descriptor**.
It is **not** an EXE table — it is RAM/BSS filled at load time, so it can only be
enumerated from a running game (which is why the dispatch map deferred it).

Enumerated across all 42 centrally declared strict-pristine anchors:

- **The pointers are identical in every level.** The kind → descriptor mapping
  itself does not change.
- Descriptors are **shared** (kinds 0 and 1 point at the *same* one) and are **not
  a contiguous array** (variable stride) — a mod must **follow the pointer**, never
  index a base by `kind * 0xC`.
- Sprite examples suggest `+0x00` renderer type (`0x1D` = sprite), `+0x02/+0x03`
  w/h, `+0x04` CLUT, `+0x06` texpage, and `+0x08..` UV-like values; those field
  meanings are not generalized to non-sprite descriptors.

The corrected post-load census proves variation at exactly
`+0x04,+0x06,+0x07,+0x08,+0x0A`. Bytes
`+0x00,+0x01,+0x02,+0x03,+0x05,+0x09,+0x0B` are invariant. `+0x04`, `+0x06`,
and `+0x07` vary for all 50 kinds; `+0x08` and `+0x0A` vary for three kinds.

The former changes at `+0x00,+0x02,+0x03,+0x09` were not original-game facts: they
entered the aggregate through `collecting_FLIK_LEVELTRAINING.movie.sav`, whose
`getStateInfo.media_path` points to ALLMODS. That save is retained only as historical
comparison evidence and is centrally classified `non_pristine`.

⚠️ This is **scene dependence, not loader-writer causality**. `loadState` restores
post-load RAM and clears non-halting watches, so cross-anchor variance cannot name
the writer. Do not patch an inferred loader. The exact next experiment is a cold
boot or real transition with a write watch over `0x80081D98..0x80082060`.

| Descriptor byte | Changes between levels? |
|---|---|
| `+0x04`, `+0x06`, `+0x07` | **all 50 kinds** |
| `+0x08`, `+0x0A` | 3 kinds each |
| `+0x00`, `+0x01`, `+0x02`, `+0x03`, `+0x05`, `+0x09`, `+0x0B` | invariant in 42 strict-pristine anchors |

## Actor `+0x7C` — a per-actor EVENT CALLBACK (and it is optional)

Found by asking the live game rather than the disassembler: across 42 centrally
declared strict-pristine anchors and **1,286 live actor instances**,
`actor_record +0x7C` holds the **entry point of a censused function 60.8% of the
time**, over **9 distinct handlers** —
`enemy_strike_contact_effect`, `actor_sound40_on_low_state`,
`mosquito_species_callback`, `aimed_object_spawn_sfx`, `play_object_sound_42`,
`actor_event_sound_trigger`, … And the `jalr` pass independently shows the game
**calling through a struct field at exactly `+0x7C`**. Two methods, one answer.

**A mod can give an actor new behaviour by installing a pointer here — per actor,
without touching code.** But:

1. ⚠️ **The field is OPTIONAL.** Only 60.8% of live actors have a callback; **the
   other 39.2% have none**, so every caller must null-check.
2. ⚠️ **An installed pointer does not persist.** Actor records are rebuilt from level
   data on every load — re-install *after the world is ready*, not when the scene id
   flips (see the load-gap law above).
3. ⚠️ **The handler's ABI is not yet characterised** — it is called with the engine's
   own argument convention.

## ⚠️ The camera struct is a DERIVED OUTPUT — writing it is theatre

`0x80095358` (written by `camera_follow_update` `0x8004DF18`) holds two triples:

- `camera_pos` `+0x00` (s32 ×3) — where the camera *is*
- `camera_target` `+0x0C` (s32 ×3) — the point it *chases*

**The follow law:** the position closes ~**0.15 of the remaining gap per frame**
toward the target — an exponential chase, not a snap.

**Neither triple is authoritative, and that is the whole safety story.** Proven by
poking each one +50,000 and watching for 24 frames:

| poke | outcome |
|---|---|
| `camera_pos` | pulled back toward the target by the follow law (drift **−39,932**) |
| `camera_target` | **recomputed from scratch** next tick (drift **−45,425**) |

So a mod **cannot move the camera by writing this struct.** It must change the
producer (`0x8004DF18`) or the inputs that producer reads. *Reading* the struct is
safe; *writing* it is theatre.

(The second triple is **not** a prev-tick mirror, which was the obvious guess — it
never equals the previous `camera_pos`, and never equals the player position.)

## Scene transitions — reset, ownership, and the load gap (WP6)

Measured across a real pristine transition (`tools/phase3_transition_reset.py`,
poll-only over a from-boot movie).

Measured across **all 16 stages** — LEVEL01 alone could not show whether these
laws generalise, and two of them only became visible in the sweep.

### ⚠️ The scene id flips 450–1170 frames BEFORE the world exists

On entry the scene id (`0x80082504`) changes when the transition *starts*, but
the actors, the player position and health are all still zero until the **disc
read completes**: 450 frames at best, **1170 in Canyon Showdown**, median 540.

**A mod that hooks "scene id changed" runs inside an EMPTY world** for 8–20
seconds. The honest ready signal is the world itself: the actor roster
(`0x8009FE04`) going non-empty, *or* `health_true` going non-zero — you need both
halves, because Bug Bar has no roster and four stages write health *after* the
roster.

### What the load does (every stage)

| | on entry (load) | on exit (to shell) |
|---|---|---|
| actor roster | **0 → N** from level data (N = 4…40; **Bug Bar loads NONE**) | **NOT freed** — all N stay resident and stale |
| plant slots | 0 → N (plants exist in level **DATA**, not only from player action) | not freed |
| contact pool | empty | empty |
| player | spawned with **`health_true := 4`** (not 7) | position/velocity/anim reloaded |

**Ownership belongs to the LOAD, not the exit.** Leaving a level reclaims
*nothing* — in all 16 stages the actor, plant and contact data simply stay in RAM
until the next load overwrites it. **Anything reading those tables from the shell
is reading the previous level.**

### ⚠️ MOD-SAFETY: four stages run the actor roster COMPLETELY FULL

The actor table is a fixed **40-slot** roster, and **Tunnels, Riverbed Run, The
Tree and Riverbed Flight all load exactly 40** — zero free slots. A mod that adds
an actor to those levels has **nowhere to put it**. (Rosters elsewhere range from
4 in Battle Arena to 38 in City Entrance.)

### Session-owned player fields (a mod must NOT reinitialise these on load)

These survive the level exit unchanged **in every one of the 16 stages**, so they
belong to the **session**, not the scene: `health_true`, `lives`, `grain_count`,
`enemy_permanence_quota`, and the seed counters. Reinitialising them on load would
silently wipe the player's progress.

### Two exceptions the sweep found (kept, not smoothed over)

- **Bug Bar loads no actor roster at all** (0 actors) — the same structural
  negative Phase 2 hit when its death probe found an empty actor table.
- **Health is written a few ticks *after* the roster** in City Entrance, Clover
  Forest, The Tree and Anthill Two, so "world ready" is not a single instant.

## Init / reset / overlay lifetime — the last of gate bullet 2

Every owned semantic address now carries **init, reset, and overlay-lifetime**
(`tools/phase3_semantic_lifetime.py`), completing the exit-gate requirement of
"owner, width, domain, readers/writers, init, reset, overlay lifetime — or an
explicit blocker."

| Class | Count | init / reset |
|---|---|---|
| **resident_rom** (EXE const tables) | 12 | load-time / **never** (immutable in ROM) — derived, not probed |
| **resident_ram** (game state) | 50 | scalars measured live; tables classified from location/writers with record-reset evidence |
| **overlay** (`training_step`) | 1 | its overlay's load / on-swap |

Of the 63 entries, 35 scalar observations were measured live and 28 table/ROM/
overlay facts were derived under the report's explicit classification rules.

⚠️ **A single transition is not ground truth.** A fresh-start movie reads
`grain_count` and `health_true` as `0 → 0` — *already zero*, not *reset*. So the
known **session-owned** fields (survive a level exit) are corroborated from the
16-stage transition sweep, never guessed from one sample: `player_lives`,
`grain_count`, `health_true`, `enemy_permanence_quota`.

Unbounded fields carry an explicit **`domain` rationale** rather than a fake numeric
range — player position/velocity are world quantities with no fixed range, and
`berry_throw` is a function, not state. Stating "unbounded by design" is the honest
form of a domain.

## Who reads and writes owned state — and what a static scan cannot see

`tools/phase3_xrefs.py` resolves, for every owned semantic address, the instructions
that read and write it (gp-relative via `gp = 0x80081D98`, and `lui`-formed absolute).
**40 of 63** owned entries have static xrefs.

⚠️ **The caveat is the finding.** **20,369 of 26,557** loads/stores in the game go
through a **runtime pointer** and cannot be resolved statically *at all*. So **"no
xrefs" never means "nothing touches it"** — it means one of:

- the state is a **table read by INDEX** (`base + idx*4`) — its consumers are enumerated
  in [[SYS_indirect_dispatch_map]], not lost; or
- it is reached through a **pointer**, or written by **overlay/mod code outside the
  resident image**.

Every such entry carries an explicit `no_static_xref_because` saying which. A zero-reader
claim that is really a limit of the method is exactly the confident-but-wrong artifact
this project keeps having to unwind.

**The registry's 43 hand-curated `writers` are now verified against the image for the
first time: 0 real contradictions.** Six are pointer-based writes the method cannot see
(tables written through a cursor — `plant_slots` via `plant_spawn`, `contact_pool` via
`contact_alloc`, the camera struct via its updater); one lives in overlay space. Both are
*scope facts*, not errors, and both are reported rather than hidden.

## The unknown-byte work queue

The live probe triages every unknown byte across the pristine anchors into
**always-zero** (likely padding), **constant** (likely config), and **varying**
(live state worth reversing). Current leads, all velocity/rotation-shaped
clusters:

- `player_block` — 40 varying bytes remain (was 46; the velocity triple and speed
  are now typed). `+0x20/21` and `+0x28/29` are the next targets.
- `actor_record` — 77 varying, a solid run `+0x14..0x23`. **Untested so far** —
  the same drainer should be pointed at a moving enemy.
- `contact_record` — 16 varying remain (was 30). `+0x26` counts down beside the
  TTL and freezes when it expires; purpose unproven.
- `plant_slot` — 23 varying.

These are hypotheses, deliberately **not** written into the registry as fields
until each is proven.

## Regeneration and evidence

| What | Command | Evidence artifact | Guard |
|---|---|---|---|
| layout + byte accounting | `python3 tools/phase3_record_types.py` | `analysis/phase3_record_types.json` | `tests/test_phase3_records.py` |
| field domains + occupancy | `python3 tools/phase3_record_types.py --probe` | `analysis/phase3_record_probe.json` | `tests/test_phase3_records.py` |
| the integrators + TTL | `python3 tools/phase3_unknown_fields.py` | `analysis/phase3_unknown_fields.json` | `tests/test_phase3_records.py::test_velocity_fields_and_ttl_are_typed` |
| transition ownership (16 stages) | `python3 tools/phase3_transition_reset.py --all` | `analysis/phase3_transition_reset.json` | `tests/test_phase3_transition.py` |
| camera authority (derived output) | `python3 tools/phase3_camera_record.py` | `analysis/phase3_camera_record.json` | `tests/test_phase3_camera.py` |
| render descriptors (snapshot variance) | `python3 tools/phase3_render_descriptors.py` | `analysis/phase3_render_descriptors.json` | `tests/test_phase3_render_descriptors.py` |
| SFX interface (callable) | `python3 tools/phase3_sfx_interface.py` | `analysis/phase3_sfx_interface.json` | `tests/test_phase3_sfx_interface.py` |
| function-pointer fields | `python3 tools/phase3_fn_ptr_fields.py` | `analysis/phase3_fn_ptr_fields.json` | `tests/test_phase3_fn_ptr_fields.py` |

Every artifact hash-pins the fixtures it rests on. One guard deliberately fails if
pristine play ever reaches the contact capacity — that would mean the allocator
hang is reachable in the retail game, which is a finding, not a nit.

## MOD consumption contract

The machine-readable form of this section lives in `config/phase3_findings.yaml`
(audited by `tools/phase3_knowledge_audit.py`). In short — **an address without
its ownership and lifecycle is not a safe extension point**:

- **Contacts free themselves by TTL expiry.** A mod that refreshes TTLs or holds
  slots open destroys the only reclamation mechanism and can reach the
  allocator's no-escape hang.
- **A velocity is a move *proposal*.** The integrator may clamp the position
  (collision/ground), so writing one does not guarantee the move. Actors have no
  Y velocity at all — to move one vertically, write **position**.
- **The scene id flips 450–1170 frames before the world exists.** Wait for the
  actor roster to populate *or* `health_true > 0`; both signals are needed.
- **The session owns the player's progression.** Reinitialising `health_true`,
  `lives`, `grain_count`, `enemy_permanence_quota` or the seed counters on load
  silently wipes it.
- **Four stages load the actor roster completely full (40/40).** There is no free
  slot to add an actor in Tunnels, Riverbed Run, The Tree or Riverbed Flight.
- **The camera struct is an output.** Reading it is safe; writing it is theatre —
  both triples decay. Change the producer (`0x8004DF18`), not the struct.
- **Render-descriptor values are scene-dependent.** Follow the pointer, never
  index by kind, and do not assume durability or a loader writer until the
  transition write trace is captured.
- **`sfx_dispatch(a0=id)` really plays sounds — but never branch on `v0`.** It is
  `0x4` whether the sound played or not; only the SPU tells the truth.
- **`actor +0x7C` is an installable per-actor callback — but it is optional (61%)
  and is rebuilt on every level load.** Null-check it; re-install after world-ready.

## Superseded claims (do not revive)

| Claim | Why it is wrong |
|---|---|
| player `+0x30` = "knockback_velocity" | It is **velocity_y**; the on-hit `-1024` is just one writer (knockback is a vertical impulse *into* it). |
| contact `+0x22` = "active_type" | It is a **TTL countdown**; the walker gate's `> 0` means *"TTL not expired"*. |
| pool occupancy = "slot has non-zero bytes" | Dead slots keep **residue** — that metric falsely reads 64/64 and would contradict the hang. |
| actor `+0x20` = velocity_y (by stride symmetry) | **Unsupported.** The retained one-actor sample does not preserve rejected Y candidates; `+0x20` and vertical ownership remain unknown. |
| the load gap is 540 frames | That is LEVEL01 only; it is a **range, 450–1170**. |
| camera `+0x0C` = a prev-tick mirror | It is the **target** the camera chases; it never equals the previous `camera_pos` nor the player position. |

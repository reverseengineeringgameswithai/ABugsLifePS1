---
kind: playbook
id: PLAYBOOK_game_solving_phase_3
name: Phase 3 - Reconstruct Semantic Architecture and State Ownership
aliases:
  - Phase 3 - Solve the Berry Vertical Slice
status: complete
created: 2026-07-11
updated: 2026-07-14
confidence: high
parent: PLAYBOOK_game_solving_roadmap
previous: PLAYBOOK_game_solving_phase_2
next: PLAYBOOK_game_solving_phase_4
depends_on:
  - PLAYBOOK_game_solving_phase_1
  - PLAYBOOK_game_solving_phase_2
---

# Phase 3 - Reconstruct Semantic Architecture and State Ownership

**Navigation:** [[Phase 2 - Build the Pristine Whole-Game Behavioral Oracle|Previous phase]] · [[Game Solving Roadmap - From Reconstruction to Reliable Modding|Roadmap hub]] · [[Phase 4 - Solve Every Gameplay and Engine Subsystem|Next phase]]

## Purpose

Convert byte reconstruction, static disassembly, and runtime observations into a
whole-game model of functions, state, assets, ownership, lifetimes, interfaces, and
indirect control flow. This phase is about the pristine architecture, not hook design.

## Scope

- Resident executable, both overlay regions, every level overlay, MEMORY.BIN, FMV.BIN,
  and known SDK/library boundaries.
- Global/player/object/contact/enemy/camera/render/audio/frontend state.
- Structs, tables, callbacks, jump tables, scripts, event programs, and descriptor
  domains.
- Asset load/fixup/ownership paths for geometry, collision, textures, models,
  animation, audio, FMV, UI, and level-specific data.
- Initialization, per-frame update, render, damage, death, reset, save, unload, and
  scene-transition lifetimes.

## Work packages

- [x] Build an ownership graph from every Phase 1 mechanic to its functions, state,
  assets, overlay, readers, writers, and lifecycle events.
- [x] Expand the semantic-state registry from a small curated set to the state needed
  by every active subsystem campaign.
- [x] Resolve all fixed-width native domains and every consumer of their selectors.
- [x] Enumerate indirect dispatches, callback tables, VM opcodes, overlay entry points,
  and dynamic program selection.
- [x] Type object, contact, enemy, projectile, seed, plant, player, camera, render,
  audio, objective, and frontend records without erasing unknown fields.
- [x] Map allocation capacity, slot reuse, ownership transfer, retirement, and reset.
- [x] Establish the complete scene/overlay/resource load and unload graph.
- [x] Generate machine-readable caller/callee/reader/writer and asset-provenance reports.
- [x] Reconcile contradictions among ASM, C, runtime evidence, asset observations, and
  existing Canon before a system campaign relies on them.

## Resolved ASM contract

Resolved ASM is necessary evidence, not semantic completion. For every boundary needed
by later reconstruction or diagnostics, record:

- Live-in/live-out registers, stack, `ra`, `hi/lo`, GTE, and delay-slot behavior.
- Displaced/original instruction effects and continuation state.
- Memory reads/writes, calls, allocation ownership, and error/early-return paths.
- Selector/table domains and initialization/reset preconditions.

These contracts initially describe the original program. Eventual hook validation is a
downstream consumer, not the organizing goal of this phase.

## Exit gate

- Every Phase 1 mechanic maps to a bounded semantic frontier rather than an isolated
  address or guessed label.
- Every original-game state used by a subsystem campaign has an owner, width, domain,
  readers/writers, initialization, reset, and overlay lifetime—or an explicit blocker.
- All indirect dispatch and overlay boundaries intersecting campaign mechanics are
  enumerated.
- Diagnostic patches can preserve original continuation state using machine-checked
  contracts.
- Unknowns remain visible and cannot silently become confirmed names or fields.

## Handoff to Phase 4

Phase 4 receives the architecture graph, semantic registry, original ABIs, typed
records, and campaign frontiers needed to close each subsystem end-to-end.

## Progress record

| Architecture area | Status | Evidence |
|---|---|---|
| Mechanic ownership | complete bounded frontier | 107/107 rows carry every required facet; 106 address-bound, one explicit not-applicable row; 88/88 cited functions and 166/166 cited state addresses owned |
| Semantic state ownership | complete bounded scope | 63 entries; 13 campaign-state groups; 63/63 xref/lifetime rows, with explicit blockers for unchanged-zero observations |
| Native domains and indirect control | complete bounded census | 134 domain rows from an independent join: 36 campaign-state scalars, 62 typed record fields, and 36 decoded dispatch selectors; 95 `jr` and 139 `jalr` sites classified or reason-bounded |
| Typed records and lifecycle | complete bounded models | 8 record views cover 12 required families; 181/524 bytes typed and every other byte explicit; 16/16 transition routes measured |
| Scene/assets/reports/contradictions | complete | Training exceptional route and unload graph mapped; exhaustive call and 327-asset provenance reports; 13-row contradiction ledger reconciled/bounded with zero open rows, including exact DuckStation source/API identity, current live-artifact freshness, deterministic Training regeneration, and exact-owned debugger lifecycle |

## Kickoff (2026-07-12) — phase opened

Phase 2 signed off by external review (oracle independently reproduced;
sixteenth-pass gate). WP1 and the WP2 seed landed as DERIVED artifacts:

- **WP1 ownership-frontier graph** — `tools/phase3_ownership_graph.py` ->
  `analysis/phase3_ownership_graph.json`: every one of the 107 registry
  mechanics resolved against the functions census, symbols, semantic-state
  registry and Canon address index. Baseline: 48 mechanics address-bound /
  57 narrative-only; 20/20 cited functions named; 39/72 cited state
  addresses semantically owned; **88 computed gaps = the phase work queue.**
  Freshness+derivation guarded by `tests/test_phase3_ownership.py`.
- **WP2 registry expansion** — `config/semantic_state.yaml` 16 -> 33 entries:
  true health, state word, grounded, kick timer, in-flight counter, pad
  held/prev words, contact pool, plant slots+cursor, enemy live table,
  chunk-31 actor records, camera struct — each with owner, width/shape,
  proven writers where known, invariants, and Phase-2 artifact evidence.
  Guard test asserts every Phase-2-proven address stays owned.

## Second increment (2026-07-12) — all three levers executed

- **Lever 1 DONE:** all 20 distinct unowned-state cites promoted into the
  semantic registry (33 -> 54 entries) with owners, widths/shapes, writers
  and Canon/artifact evidence. State ownership: 118/123 cited addresses.
- **Lever 3 (WP4) first increment DONE:** `tools/phase3_dispatch_map.py`
  decodes the three campaign-critical jump tables from the pristine EXE —
  mover-VM opcodes (26, all named, op9=branch_if_s3 confirmed), berry throw
  (5 distinct POWER-setting entry offsets inside berry_throw_dispatch),
  plant behaviors (13, all named; index = type-2 cross-checked against the
  brown/green seed Canon). 44/44 slots resolved, 0 gaps. Offline guards +
  local_media freshness test. PLUS the full WP4 bound: every indirect-
  dispatch SITE in resident censused code enumerated — 234 total (95
  jr-table dispatch, 139 jalr callbacks); the VM interpreter's jr at
  0x8004C220 verified in the bytes (sltiu 26 bound check + lw from
  0x8001B2F4). **94 jr sites without a decoded table = the computed WP4
  frontier.** object_pointer_list 0x80096B98 is LOAD-TIME RAM — enumerate
  per-scene via the debugger.
- **Lever 2 first tranche:** 43 narrative-only rows bound with real,
  evidence-backed addresses (plant handlers from the dispatch map, berry
  chain entries, bonus streak counters, enemy shared-architecture lanes with
  explicit "family program index unpinned" honesty markers, render/actor/
  save subsystem anchors). Frontier: **48 -> 91 address-bound; 88 -> 14
  open gaps.**

## Third increment (2026-07-12) — WP7 scene/overlay load graph; FRONTIER GAPS = 0

The last 14 gaps all needed the same missing object: the campaign's resource
routing. It turned out to be three ASCII tables in the resident EXE, found by
scanning the pristine image for level-ish strings and then locating the code
that materializes each base — see [[SYS_scene_asset_load_graph]].

- **scene asset table `0x8001AD0C`** (15 × 0x10, `"levelNN\levelXY"`),
  consumer `0x8003CFDC` in `resource_id_dat_load_dispatcher`.
- **GFX loading-screen table `0x8001AE98`**, consumer `0x8003F4B8`.
- **level BIN table `0x8001B174`**, consumer `0x80046718` in
  `level_file_path_build`.

**Load law:** row index = scene_id − 1; the disc DIRECTORY selects the overlay
pair (`LEVELNN_LEVEL`/`_LEVEL1`), the ASSET PREFIX selects the sub-level data
and loading screen. Disc dir numbers therefore do NOT track scene ids (scene 11
loads `level02\level4b`) — a regression test pins that.

**Cross-verified against independent runtime evidence:** all 15 rows resolve to
the scene ids the Phase-2 `go_to_end` movies actually reached. Static decode and
observed replay agree on every campaign stage; neither was derived from the
other. Training (scene 17) is OFF-TABLE and reported as a computed gap, not
silently omitted.

With the 13 stage rows, D18 (Bug Bar = scene 14) and E12 (audio =
`sfx_dispatch` `0x80050994` + glue `0x80050E6C` + XA position read
`0x8006DCB0`) bound, and the three routing tables owned in the registry:

**WP1 frontier: 105/107 mechanics address-bound (the other two are
`not_applicable`), 52/52 cited functions named, all cited state owned,
computed gaps 88 → 14 → 0.** Semantic registry: 16 → 57 entries.

### Phase-2 correction discovered here

`0x80050994` is **`sfx_dispatch`**. The A11 seed-impact "arm" therefore reads:
*play impact sound (id −4)* + *write the knockback* (`sh -20 → enemy+0x6C`) —
the `jal` was never a damage call. The behavioural claim is unchanged (the
knockback write is still the damage), but the mechanism text in
`analysis/phase2_final_action_pairs.json` and its generator were corrected
rather than left to read as if two damage calls existed.

## Fourth increment (2026-07-12) — WP5 typed records + WP6 lifetimes

`config/record_types.yaml` + `tools/phase3_record_types.py` →
[[SYS_record_layouts_and_lifetimes]]. Four core records (player block, contact
record, actor record, plant slot) typed under the gate's own rule — **typing must
not erase unknown fields** — mechanised as full byte accounting: every byte is a
declared field or an explicit UNKNOWN span. **104/412 bytes typed (25.2%);** the
rest is *named as unknown*. The layout validator immediately caught a real error
(`berries_in_flight` is u8, not u16, or it swallows `equipped_berry`).

**WP6 occupancy, and a trap worth remembering.** The first probe read the contact
pool at 64/64 — impossible, since a full pool hangs the allocator. The metric was
wrong: dead slots keep RESIDUE, so "has non-zero bytes" is not occupancy. Using
the game's own predicates (and there are two: the walker/live gate and the
allocator's skip test) across all 42 centrally declared strict-pristine anchors, the contact pool peaks at
**4 of 64 (headroom 60)**. **The capacity hang is a mod-introduced risk, not a
latent retail bug** — and a test now fails if pristine ever reaches capacity.

Every unknown byte is triaged (always-zero / constant / varying) into a work
queue. The varying clusters are velocity/rotation-shaped and held as hypotheses,
not written in as fields.

## Fifth increment (2026-07-12) — draining the unknown-byte queue

`tools/phase3_unknown_fields.py`: capture a whole record every frame while the
object moves, then promote a candidate only if it **exactly equals the per-tick
position delta**. The berry's known gravity is the built-in control, and the tool
rediscovered **128/frame² from the raw bytes** — so its verdicts can be trusted.

Typed: **131/412 bytes (25.2% → 31.8%)**. Both integrators are now explicit —
player velocity `+0x2C/0x30/0x34`, contact velocity `+0x0C/0x10/0x14`, contact
`gravity_per_tick = 128` at `+0x18`, player horizontal speed at `+0x38`.

**Two corrections it forced.** `player +0x30` is **`velocity_y`**, not
"knockback_velocity" — the old name described one *writer* (the −1024 on-hit
impulse) and mistook it for the field's *meaning*. And `contact +0x22` is a
**`lifetime_ttl` countdown**, not an "active_type": it ticks down to 0 and the
slot is **retired** there.

**That last one explains WP6's open question.** Contacts *free themselves* by TTL
expiry — which is precisely why pristine play peaks at 4 of 64 slots and never
meets the allocator's no-escape hang. A mod that refreshes TTLs or holds slots
open destroys the mechanism that keeps the pool drained.

Method traps recorded (each produced a wrong answer first): the 30 Hz logic
cadence; velocity as a *move proposal* that collision can clamp; the player's
velocity written *after* the move vs the berry's *pre-integrated*; and above all
**never accept a match on a zero delta** (jumping in place makes `0 == 0` "prove"
half the record).

## Sixth increment (2026-07-12) — actor motion + WP6 transition ownership

**Actor motion typed; the former Y disproof is superseded.** The retained drainer
run, pointed at one Level01 actor, confirms `velocity_x +0x1C` (19/19 moved
frames) and `velocity_z +0x24` (12/19, with collision/ground clamps). It does not
retain rejected Y candidates and did not execute the advertised 42-anchor/92-tick
sweep. The campaign-wide “actors have no stored Y velocity” claim therefore does
not reproduce. `+0x20` remains unknown: do not infer it from stride symmetry, and
do not exclude it until a multi-family vertical-motion artifact retains all
candidates. Records at this increment were **139/412 bytes typed (33.7%)**.

**WP6 transition ownership** (`tools/phase3_transition_reset.py`, poll-only over
a from-boot movie, both directions):

- ⚠️ **The scene id flips ~540 frames BEFORE the world exists.** On entry the id
  changes when the transition starts, but actors/player/health are all still zero
  until the disc read completes. **A mod hooking "scene changed" runs inside an
  empty world** — wait for the actor roster to populate instead.
- **The load owns the world; the exit frees nothing.** Entry: actors 0 → 30,
  plant slots 0 → 2 (plants exist in level DATA, not only from player action),
  player spawned with `health_true := 4`. Exit: the actor/plant/contact data stays
  resident and stale until the next load overwrites it.
- **Session-owned player fields** (survive the exit, so a mod must not
  reinitialise them on load): `health_true`, `lives`, `grain_count`,
  `enemy_permanence_quota`, seed counters.

## Seventh increment (2026-07-12) — the transition laws, generalised to all 16 stages

LEVEL01 could not tell me whether the WP6 ownership laws were general, so the
sweep now runs **every stage** (`tools/phase3_transition_reset.py --all`). They
hold 16/16 — and two things only became visible at that scale:

- **The load gap is 450–1170 frames** (median 540), not a single number. A mod
  hooking "scene changed" runs inside an empty world for 8–20 seconds.
- ⚠️ **MOD-SAFETY: four stages run the fixed 40-slot actor roster COMPLETELY
  FULL** (Tunnels, Riverbed Run, The Tree, Riverbed Flight). A mod adding an actor
  to those levels has nowhere to put it. This is invisible from LEVEL01, which
  loads 30.

Two honest exceptions, asserted rather than smoothed over: **Bug Bar loads no
actor roster at all** (matching the structural negative Phase 2 hit on its death
probe), and **health is written a few ticks after the roster** in four stages —
so "world ready" needs both signals, not one.

Also this pass (WP9): the semantic registry and the typed records disagreed on the
name of five addresses; reconciled toward the more precise term (e.g.
`native_berry_selector` → `player_equipped_berry`, and the anim pair explicitly
named a FRAME COUNTER so nobody mistakes it for a state id again).

## Eighth increment (2026-07-12) — knowledge closure under the new Definition of Finished

The roadmap now says a finding is not FINISHED because it was demonstrated: it must
be banked (provenance, machine representation, reproducible evidence, an executable
guard, Canon placement, a **MOD consumption contract**, clean-checkout durability,
and explicit confidence/supersession) — and that phase closure must *show* this, not
assert it.

I audited my own Phase-3 findings against those eight requirements and **three of
them failed**:

- **Provenance:** all three live artifacts named their fixtures but did **not
  hash-pin** them — a fixture that can change silently underneath a claim is not
  provenance. Now pinned (record probe 43 fixtures, transition sweep 17, drainer 3,
  and the EXE in both static tools).
- **Placement/linkage:** Canon pages did not link the evidence artifacts a reader
  would need.
- **MOD contract:** the findings had mod-safety prose scattered in notes but no
  systematic contract stating what a mod may **not** assume.

Banked as `config/phase3_findings.yaml` (7 findings, each with the eight fields) +
`tools/phase3_knowledge_audit.py`, which **checks** each requirement mechanically
rather than trusting the registry's prose: a guard must really define the named
test, a Canon page must really link its evidence, fixtures must really be pinned,
dependencies must really be tracked in git.

**Falsified, so it is not another self-grading artifact:** pointing a finding at a
guard test that does not exist, or stripping a fixture pin from an artifact, each
flips that finding to GAP and the exit code to 1. Result: **7/7 findings FINISHED,
0 open gaps.**

Superseded claims are now recorded machine-readably so nobody revives them —
`knockback_velocity`, `active_type`, "occupancy = has non-zero bytes", the actor
`+0x20` stride-symmetry guess, and "the load gap is 540 frames".

## Ninth increment (2026-07-12) — the camera record, and a contract you cannot get from a name

Typed the camera record (`0x80095358`, 5th record family; **163/508 bytes, 32.1%**)
— but the useful part was not naming the fields, it was asking **which of them, if
any, a mod can actually write.**

- The struct holds two triples: `camera_pos` `+0x00` and, at `+0x0C`, **the target
  it chases** (*not* a prev-tick mirror, which was the obvious guess — it never
  equals the previous position, nor the player's).
- **The follow law:** the position closes ~**0.15 of the remaining gap per frame**
  — an exponential chase.
- ⚠️ **Neither triple is authoritative.** Poke `camera_pos` +50,000 and the follow
  law pulls it back (drift **−39,932**); poke `camera_target` and it is
  **recomputed from scratch** next tick (drift **−45,425**). **The camera struct is
  a DERIVED OUTPUT: reading it is safe, writing it is theatre.** To move the camera
  a mod must change the producer (`camera_follow_update` `0x8004DF18`) or the inputs
  it reads.

That is exactly the sort of thing the new Definition of Finished exists to force
out: a symbol name would have said "camera position" and a mod author would have
wasted a day poking it. Banked as finding `camera_is_a_derived_output` with its
guard, contract and supersession — **8/8 findings FINISHED, 0 gaps.**

## Tenth increment (2026-07-12) — render descriptors, and the WP4 residual closed

`object_pointer_list` `0x80096B98` was the one structure the dispatch map explicitly
deferred: it is **not** in the EXE, it is RAM/BSS filled at load time. Enumerated
live across all 42 centrally declared strict-pristine anchors
(`tools/phase3_render_descriptors.py`):

- **The kind → descriptor pointers are identical in every level** — the mapping
  itself is stable.
- Descriptors are **shared** (kinds 0 and 1 point at the same one) and **not a
  contiguous array** — a mod must *follow the pointer*, never index `base + kind*0xC`.
- Iteration-5 strict-origin regeneration corrected the earlier aggregate: post-load
  bytes `+0x04,+0x06,+0x07,+0x08,+0x0A` vary between anchors; bytes
  `+0x00,+0x01,+0x02,+0x03,+0x05,+0x09,+0x0B` are invariant. `+0x04/+0x06/+0x07`
  vary for all 50 kinds; `+0x08/+0x0A` vary for three. The former changes at
  `+0x00,+0x02,+0x03,+0x09` came from an ALLMODS-origin Training save and are
  superseded, not original-game behavior.
  This is **scene dependence, not loader-writer causality**: save-state snapshots
  cannot identify the writer. A cold-boot/transition write trace remains the exact
  bounded next experiment.

The durable contract is therefore narrower: follow pointers and do not assume a
one-time descriptor edit persists, but do not patch an inferred loader. Banked as
partial finding `render_descriptors_are_loader_patched` (legacy ID retained for
machine-reader compatibility) with the writer residual explicit.

## Eleventh increment (2026-07-12) — the SFX interface contract (DoF #5)

`sfx_dispatch` `0x80050994` is a boundary a mod would love to use ("play a sound"),
and it is the function both seed-impact arms call. Characterised by **calling it**
rather than reading it — invoke each id on a fresh pristine anchor and ask the
**SPU** whether a voice actually keyed on (`tools/phase3_sfx_interface.py`).

- **`a0` = the sfx id, and it is SIGNED** (both seed arms pass `-4`). Swept
  `-24..48`: **27 ids play**, each starting a **distinct sample** — no aliases.
- ⚠️ **`v0` is NOT a success flag.** It reads `0x4` for every id that plays **and
  for 36 ids that stay silent**. *"It returned 4, so it worked"* is precisely the
  wrong inference — only the SPU proves a sound started.

I had written "v0 is constant" into the tool's docstring on the first pass; the
sweep disproved my own claim (six distinct return values), so I corrected the tool
**and** regenerated the artifact rather than leave a false statement banked. The
sweep reproduces identically across three runs.

Banked as `sfx_dispatch_interface` — **10/10 findings FINISHED, 0 gaps.**

## Twelfth increment (2026-07-12) — the jr frontier: 36 tables decoded, and a 2x overstatement corrected

The dispatch map's "**94 jr sites with undecoded tables**" was the biggest WP4
residual. Backward-slicing the compiler idiom (`sltiu` bound → `sll` → `lui`+`addu`
→ `lw` → `jr`) resolved it — and the headline is a **correction**, not a conquest:

| Class | Count |
|---|---:|
| **table dispatch** (decoded) | **36 tables, 869 entries — every target lands in a named function** |
| **computed code jump** | **45** — `jr base + (index << k)`: an unrolled loop / jump island. **There was never a table.** |
| unresolved | 14 (8 constant-target `ori` forms, 2 without a bound, 2 wrong slices *refused*, 2 misc) |

⚠️ **Nearly half the `jr` sites are not dispatches at all.** Calling them "undecoded
tables" overstated the frontier by ~2×, and a tool that "recovered" a table address
for one would be pointing at **instructions, not pointers** — patching there
corrupts code.

**Self-check:** the slicer independently rediscovers all three tables I had decoded
by hand (mover-VM, berry throw, plant behaviours). Slices whose entries do not
resolve to censused code are **refused**, not reported — a wrong table is worse than
a missing one.

Banked as `jr_dispatch_frontier_resolved` — **11/11 findings FINISHED, 0 gaps.**

## Thirteenth increment (2026-07-12) — the 139 `jalr` sites: the game's own hook mechanism

The other half of WP4. A `jalr` calls through a function **pointer**, and where that
pointer comes from decides whether a mod can redirect it:

| Source | Count | Meaning |
|---|---:|---|
| **global callback slot** | **99** (30 distinct) | a fixed address holding a handler — **write it and the call redirects, with no code patching at all** |
| **function-pointer field** | 36 | loaded from a record at a fixed offset (`+0x8` ×9, `+0x10` ×8, `+0x14` ×4 …) — a **typed-record** fact |
| unresolved | 4 | with reasons |

**Resolved LIVE** (no static read can tell you this): the slots currently hold
`trapIntrVSync`, `def_cbsync`, `def_cbread`, `music_loop_poll`, `printf`, the whole
`pad_direct_*` family, `_dws`. **Twelve slots hold NULL.**

**A callback slot is a far safer extension point than a code cave** — it is the
redirection mechanism the game already uses on itself. But three things a mod must
**not** assume, and I have written all three into the contract rather than let the
result read as an invitation:

1. **A NULL slot is not a "free hook."** Whether the call site guards against NULL
   is **unverified**; a half-installed slot jumps to garbage.
2. **The slots are not equal.** `trapIntrVSync`, `def_cbsync`, `def_cbread` run in
   **interrupt context** — a replacement must be interrupt-safe and preserve the ABI.
3. **Handlers may not be constant.** They were read at *one* anchor; a per-scene
   sweep is still owed.

Banked as `jalr_callback_slots` — **12/12 findings FINISHED, 0 gaps. WP4 is now
complete for both `jr` and `jalr`.**

## Fourteenth increment (2026-07-12) — the actor event callback (WP4 x WP5 join)

The `jalr` pass proved 36 calls go through a function pointer loaded from *some*
record at a fixed offset, but static slicing cannot say **which** record. Live data
can: for every typed record, at every 4-byte offset, across every anchor — does the
value point at the **entry point of a censused function**?

**`actor_record +0x7C` is a per-actor EVENT CALLBACK.** Across 42 centrally
declared strict-pristine anchors and **1,286 live actor instances** it holds a real
entry point **60.8% of the time**, over
**9 distinct handlers** (`enemy_strike_contact_effect`, `actor_sound40_on_low_state`,
`mosquito_species_callback`, `aimed_object_spawn_sfx`, `play_object_sound_42`,
`actor_event_sound_trigger`, …). And the `jalr` pass **independently** shows the game
calling through a struct field at exactly `+0x7C` — two methods, one answer.

**A mod can give an actor new behaviour by installing a pointer here, per actor,
without touching code.** Three hazards, all in the contract:

1. ⚠️ **The field is OPTIONAL** — only 61% of actors have one; **39% have none**, so
   callers must null-check.
2. ⚠️ **An installed pointer does not persist** — actor records are rebuilt from level
   data on every load; re-install *after world-ready*, not on the scene-id flip.
3. ⚠️ **The handler ABI is uncharacterised.**

Banked as `actor_event_callback_field` — **13/13 findings FINISHED, 0 gaps.** The
remaining `jalr` struct-field offsets (`+0x0`…`+0x3C`) belong to records not yet
typed, which is now the sharpest pointer at what WP5 should attack next.

## EXIT GATE — MET (ratchet iteration-6 Training/lifecycle closure, 2026-07-14)

The iteration-5 verifier found that the Training fixture generator still trusted an
already-provisioned save instead of reproducing its claimed from-boot recipe. It also
exposed an external-launcher startup race that could remove the PID file while the
exact requested DuckStation process remained live, after which cleanup falsely
reported no owner. These were evidence-durability failures: the retained save bytes
were correct, but neither their origin nor the owned process lifecycle was executable.

The Training generator now pauses the guest before starting playback, proves the
playback and advance both start at index 0, advances to index 6904, and requires
emulator frame 6905, cycle 3909055795, PC `0x8004FEA4`, and scene 17. Every invocation
saves a new transient candidate, requires its SHA-256
`d41c000504313cccfcf2920dd928ab864b27bf71e699b05a6c0b7d4e030a8795` and
2,152,414-byte size to match both the central declaration and provisioned external
fixture, then records exact PID-scoped cleanup. This supersedes the nominal frame-6900
recipe: that RPC boundary raced because the guest ran between separate playback calls.

The tracked launcher wrapper recovers the race only when exactly one process matches
the requested executable, `XDG_CONFIG_HOME`, `XDG_RUNTIME_DIR`, an open descriptor
inside the fresh config, and three stable authenticated API probes. Failed starts stop
only that exact owner; ambiguous or foreign processes are refused. Stop remains tied
to the config/PID guard, waits for exit, and treats a dead zombie as stopped rather
than inventing an orphan. Unit tests falsify executable, environment, config ownership,
and zombie handling.

All twelve pristine live artifacts were replayed after the final shared provenance and
launcher helper changes. The results remain: 42/42 strict-pristine aggregate anchors
with zero refusals; 139 bounded `jalr` sites; 63 state lifetimes; 27 distinct playable
SFX IDs; Thud id `0x24` with the HP-zero retirement edge; A07 as a 193-trial bounded
negative; and 16/16 transition stages with zero skips, a 450–1170-frame load gap, and
exact owned-PID/private-sibling cleanup. The regenerated contradiction ledger contains
13 rows: six reconciled, seven bounded, and zero open. Diagnosis, low-level identities,
the complete replay matrix, and validation commands are banked in
[[EXP_2026-07-14_phase3_ratchet_iteration6_training_anchor_lifecycle]].

## Prior EXIT GATE evidence — ratchet iteration-4 current-live freshness closure

The iteration-3 verifier reproduced the static, build, hook, fixture, and behavioral
predicates but rejected the green gate after current-toolchain live regeneration rewrote
all twelve retained artifacts. Seven declarations named an obsolete release hash, four
artifacts retained an older dirty-source identity, the inventory never compared those
declarations with actual external bytes, and transition replay treated a per-run
snapshot-manifest digest as semantic.

Declarations now derive from the current RPC manifest and verify bytes at their named
paths. Every regular live run retains and is checked against the current RPC semantic,
source, and selected-binary identity; the gate independently re-extracts the external
fork. Immutable-snapshot normalization ignores only per-run paths/sibling and snapshot-
manifest identity while retaining the running binary and 207-file support-tree digests.
Falsification tests reject stale retained source identity and a changed support tree.

The complete pristine twelve-artifact matrix was replayed after the external fork
stabilized at 203 methods and 88 dirty paths. All 42-anchor aggregates refused zero,
A07 remained a 193-trial bounded negative rather than disproven, and the immutable
transition run measured 16/16 stages with zero skips, a 450–1170-frame load gap, and
exact owned-PID/sibling cleanup. Machine identities, substantive observations, the
discarded 87-path intermediate replay, guard design, and clean-checkout results are
banked in [[EXP_2026-07-14_phase3_ratchet_iteration4_current_live_freshness]].

## Prior EXIT GATE evidence — iteration-10 hook/toolchain durability closure

The iteration-2 fresh verifier found three independent overclaims under the green
iteration-9 gate. `blackberry:terrain_emitter_color` was counted as an exact discharge
although both its recovered liveness extent and post-build confidence were degraded;
the hub still said continuation clobbers were not checked; and the gate trusted a
retained DuckStation manifest even after current dispatcher and binary bytes changed.
An all-stage replay also reached provenance finalization only to find its canonical
binary path had been replaced in place.

Iteration 10 makes those failures executable. Hook aggregation classifies the recovered
extent as **5 proven + 9 exact-confidence discharged + 1 degraded**, while retaining
zero hard violations, owed modules, refusals, or unverified caves against the pinned
diagnostic image. The cross-layer contradiction ledger consumes that raw confidence
and reconciles this note, the hub, and the finding registry. The Phase-3 gate now
re-extracts the current dirty external fork on every run instead of trusting retained
counts or a separately invoked freshness command.

Long transition replays use `tools/live_toolchain_snapshot.py`: it verifies the current
RPC manifest, creates an exclusive read-only executable sibling in the canonical Qt
application directory, privately copies the hash-pinned client/launcher under `/tmp`,
and pins the remaining release support tree. This preserves resource discovery while
making the running inode independent of canonical rebuilds. Finalization revalidates
the exact PID, config ownership, running inode hash, support tree, source dependencies,
and pristine mounted media before stopping only that PID and removing only the exact
owned sibling. The fresh `--all` replay measured **16/16 stages with zero skips** and
retained this atomic provenance. Commands, identities, the relocation failure, causal
confirmation, and cleanup are banked in
[[EXP_2026-07-14_phase3_iteration10_hook_toolchain_closure]].

## Prior EXIT GATE evidence — iteration-9 debugger API/source reconciliation

The iteration-1 fresh verifier rejected the iteration-8 branch after independently
enumerating the exact DuckStation source used by decisive live evidence. The current
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` dirty fork dispatches **191 methods**
(114 at HEAD + 77 dirty-only, zero removed), while the authoritative Markdown still
described the obsolete 141-method GAP-0001 snapshot and Canon claimed 143. That
documentation/source contradiction violated the exact-fork and knowledge-consistency
requirements even though the gameplay evidence itself reproduced.

Iteration 9 adds `tools/phase3_duckstation_rpc_manifest.py` and the machine artifact
`analysis/phase3_duckstation_rpc_manifest.json`. The generator brace-scopes
`IsKnownMethod`, independently proves that its set equals the actual dispatch-handler
branches at HEAD and in the worktree, retains the complete 82-path dirty status and
hash, pins the dispatcher, four current API docs, client README, launcher, client, and
both normal/release Phase-3 binaries, then deterministically renders
`tools/duckstation_rpc_method_manifest.md`. `--check` re-extracts the current fork and
fails on any source, binary, method, Markdown, or Canon drift. Safe tests recompute the
retained sets/counts and falsify omissions; the Phase-3 knowledge audit and gate now
consume the same low-level predicate. The contradiction ledger's eleventh row records
the obsolete 141/143 surface as superseded and reconciled.

No original-game claim or retained live generator changed, so this repair does not
invent a new gameplay replay or invalidate the iteration-7/8 pristine evidence. It
binds the existing runs to the exact source/binaries they already record. Commands,
hashes, observations, guard falsification, and clean-checkout results are banked in
[[EXP_2026-07-14_phase3_iteration9_rpc_manifest_freshness]].

## Prior EXIT GATE evidence — iteration-8 render-replay durability

The recovery verifier rejected the iteration-7 durability claim after a fresh render
replay rewrote semantically identical evidence: Python integer descriptor-map keys
were compared with string keys reloaded from JSON. The inventory and gate also stayed
green while tracked evidence was modified. Iteration 8 JSON-normalizes the render
document at its write boundary, adds a no-rewrite regression for the exact integer-key
case, and makes inventory closure require an empty tracked-upstream mutation list. A
second mutation test proves both inventory and gate exit 1 when the render artifact is
dirty and recover only after it is restored.

The render generator was replayed in a newly created isolated config on the verified
pristine CUE/BIN: 42/42 strict-pristine anchors reproduced the stable pointer table and
the same five varying offsets. A separate detached checkout provisioned only from the
1,262-entry central set replayed it again, printed `semantic replay matched`, preserved
the committed artifact byte-for-byte, rebuilt the pinned diagnostic image, discharged
all 15 hook rows, kept inventory/gate green, and ended clean. Exact commands, identities,
hashes, observations, and cleanup are banked in
[[EXP_2026-07-14_phase3_iteration8_render_replay_durability]]. Iteration 7's semantic
architecture remains valid, but its clean-replay durability claim is superseded here.

The iteration-6 fresh verifier rejected closure because it found a dependency edge
the evidence inventory did not model: 11 committed live artifacts retained obsolete
`tools/live_session_provenance.py` hashes, while the inventory and gate still reported
CLOSURE-READY/MET. A fresh camera run then changed the committed artifact by adding
the current helper hash, its central save-fixture declaration, and embedded-state
media hash verification. Iteration 7 makes the generator and shared helper explicit
dependencies of every live artifact, requires those retained hashes to match current
bytes, and rejects missing state/media provenance. Two mutation guards independently
prove that helper drift or missing embedded-media evidence reopens the inventory and
gate.

All 11 invalidated artifacts were replayed in newly created isolated configurations
on the hash-verified pristine CUE/BIN. Their semantic observations reproduced: the
16-stage load gap remains 450–1170 frames; all 63 lifetime entries remain bounded;
the camera remains a derived output; 139 `jalr` sites and the actor `+0x7C` callback
field remain classified; the 42-anchor descriptor and function-pointer aggregates
accept only strict-pristine saves; 27 SFX IDs key 27 distinct samples; the typed
motion/TTL laws reproduce; Thud's HP edge reproduces; and the 193-trial A07 battery
remains a bounded negative rather than a disproof. Exact ports, config paths, hashes,
commands, observations, and cleanup are banked in
[[EXP_2026-07-14_phase3_iteration7_live_helper_freshness]].

Iteration 5 regenerated every low-level predicate after rejecting the same-serial
Training save whose embedded media path points to ALLMODS. A replacement Training
state was initially described as derived at nominal target frame 6900 (saved at
emulator frame 6905, scene 17), centrally pinned, and independently validated before
use. Ratchet iteration 6 supersedes that nominal recipe: pause-first playback index
6904 is the deterministic boundary that reproduces those exact save bytes. The three
breadth aggregates now accept 42/42 strict-pristine
anchors, retain 42 pre-load state inspections each, and reject none. The
authoritative surfaces are `analysis/phase3_coverage_matrix.json` (WP1-WP9),
`analysis/phase3_evidence_inventory.json` (every generator/artifact/live provenance),
`analysis/phase3_contradictions.json` (cross-layer reconciliation), and the five-bullet
`analysis/phase3_gate_audit.json`. Retained verdict fields are never accepted without
recomputation by their generators and falsification guards. Exact live identities,
commands, observations, and bounded inferences are banked in
[[EXP_2026-07-13_phase3_iteration3_closure]]. The fresh verifier's iteration-4
durability correction and historical 1,261-input provision plan are banked in
[[EXP_2026-07-14_phase3_iteration4_durability_closure]]. The strict-origin diagnosis,
replacement-fixture recipe, corrected render-byte census, replay-profile ordering/pause
guards, and final 1,262-input clean-checkout reproduction are banked in
[[EXP_2026-07-14_phase3_iteration5_strict_pristine_training_anchor]]. Iteration 4's
architecture result is retained, but its claim that all aggregate anchors were
pristine is explicitly superseded.

Iteration 6 directly reproduces the verifier's remaining clean-provision path. It
classifies `emulator.getStateInfo.timestamp` as host-file metadata while keeping the
fixture hash, size, state version, embedded media, and observations semantic; an actual
fresh 1,262-input clone then preserves the record-probe artifact byte-for-byte across
42/42 strict-pristine anchors. Every live inventory mode now declares an exact
launcher, binary/hash, pristine media pins, and executable settings profile, with
closure guards against omissions or retained-evidence mismatches. The diagnosis,
causal test, exact isolated replay, and clean-clone results are banked in
[[EXP_2026-07-14_phase3_iteration6_clean_provision_replay]].

That record-probe durability result remains valid, but iteration 6's broader closure
claim is superseded by iteration 7 because it did not compare the shared helper hash
for every other retained live artifact.

| Bullet | Result |
|---|---|
| 1. Mechanic frontier | **MET** — 107/107 facet-complete rows and 0 open ownership gaps. A07 is an `external_lead`: the fresh 193-trial whole-player-block watch is a **bounded negative, not an absolute disproof**. F09/Thud remains `partial`, with id 0x24, HP `+0x6e`, and the HP≤0 retirement edge bound. |
| 2. State ownership | **MET** — 63/63 entries have owner, width, domain, readers/writers, init, reset, and overlay lifetime or a structured blocker; 35 measured live and 28 derived. |
| 3. Dispatch + overlays | **MET** — all 234 indirect sites bounded; 20 overlays plus Training's resident/shared exceptional route and load/unload ownership mapped. |
| 4. Hook contracts | **MET** — all 15 hook caves accounted (5 proven + 9 exact-confidence discharged + 1 degraded recovered-extent row) against the PINNED full 4-code-mod image; 0 cave-unverified, 0 owed, 0 refused, 0 hard violations. Real CFG backward-liveness fixpoint + arity fixpoint; teeth proven by deliberately-unsafe fixtures. |
| 5. Unknowns visible | **MET** — all 19 findings have confidence and residuals; 8 record views cover every required family with 181/524-byte accounting intact. |

The gate stays **falsifiable**: `tests/test_phase3_gate.py` strips a binding and confirms
bullet 1 reopens, corrupts the overlay map (bullet 3), and mismatches the image hash
(bullet 4). It now also drifts a clean-checkout regeneration product and requires the
upstream knowledge report and external fixture set to become stale/fail. Carried into
Phase 4 (bounded, non-blocking): F09/D18 are `partial` — the
rolling-arena transform and Thud's mover-VM attack-phase FSM (0x800777A6) remain undecoded.

### Iteration-4 durability correction

The iteration-3 architecture evidence was retained, but its clean-checkout claim was
superseded after the verifier exposed missing derived inputs, hidden `OVL/` authority,
stale deterministic products, and destructive JALR `--no-live` refresh. The repaired
machine layer centrally pins 651 derived assembly sources, 25 r2/analysis metadata
files, and three Canon-referenced disassembly listings; the preservation set now
contains 931 fixtures. One guarded provisioner verifies all 1,261
fixture/staging/media inputs and
refuses mismatched existing targets. Overlay builds consume only pristine staged pins.
JALR static refresh preserves a fresh, pristine-verified 30-slot live run byte-for-byte.
The complete safe and local-media suites report 356 and 27 passes respectively.

### What the audit corrected (all fixed)

- **Lifetime misclassification** — 12 BSS runtime fields (scene_id, pad words, bonus
  counters, allocation cursors) were labelled immutable ROM by an address threshold.
  Now driven by the xref **writers**: written ⇒ mutable RAM, never-written ⇒ ROM.
- **Schema contradiction** — `berries_in_flight` was u16 in the registry, u8 in the
  record schema; fixed to u8, with a cross-schema reconciliation test.
- **Ownership inflation** — the graph counted addresses found only in `next`-experiment
  prose as confirmed bindings (5 rows, incl. Thud). Now scans **only bindings**, and a
  bare Canon note no longer suppresses an ownership gap (a note documents; it does not
  own). Also recognises the canonical `FUNC_`/`MEM_` reference form.
- **Invented gate permission** — bullet 1 was waiving A07 with a "blocker" clause it
  does not contain. Removed; A07/F09 are honest residuals.
- **Vacuous bullet 4** — passed on `hard_violations==0` with 0 discharges against an
  **untracked, unpinned** image. Now requires the patched image be reproducibly built
  (`python3 mod/build.py --no-disc --profile diagnostic`) and hash-pinned, and every
  obligation accounted; a module absent from the built image is "owed", not passed.
- **Circular audit** — the knowledge audit treated the gate as a finding while the gate
  consumed the knowledge-audit result. Decoupled: the gate finding was removed, and
  bullet 5 now computes directly from the findings registry + record accounting.
- **False commit** — the earlier commit `5a2cbfe` claimed the Obsidian handoff was
  committed and the gate falsified three ways; neither was true. Both are now real.

## Carried into Phase 4 (bounded, non-blocking — the gate is MET)

These deepen findings that are already at a bounded frontier; none reopens the gate.

- **A07_spin** — retained as an `external_lead`. Static analysis plus the 193-trial,
  block-wide runtime writer battery is a bounded negative. Only the external source's
  exact input sequence, context, and expected effect can resolve the remaining claim.
- **F09_bug_bar / D18_thud** — `partial`. Boss identity, damage path, and defeat are
  BOUND (id 0x24, HP `+0x6e`, retire via `mover_updater` `FUNC_8004D224`). Still
  open: the rolling-arena transform and Thud's mover-VM attack-phase FSM.
- **Lifetimes / hook contracts** — Phase 4 may build on them, but must not treat
  them as re-derivable WITHOUT the committed evidence (the lifetime classifier's
  RAM-vs-ROM rule and the hook discharge both depend on the pinned artifacts).

### Second re-review (2026-07-13) — corrected before re-closing
A follow-up audit caught real defects in the first "MET" claim; all fixed and
re-verified: (1) the lifetime classifier mislabeled pointer-written RAM ABOVE the
loaded image (`0x80082800`) as immutable ROM — now RAM by location; (2) the A07
disproof watched only the mode word — broadened to the whole player block so a
kick-like separate-field move cannot hide; (3) the A07/Thud findings were not in the
findings registry and the hook finding was stale — banked and refreshed; (4) the
pinned `--no-disc` build required untracked `REBUILD/abl.xml` — `lba_for` is now
skipped under `--no-disc`; (5) the live tools now capture mounted-media identity.

## Iteration-3 architecture closure

- **WP1:** 107 mechanic rows, every one facet-complete; 106 address-bound and one
  explicit not-applicable row; no computed gaps.
- **WP2/WP3:** 13 state-scope groups cover all campaign substrates; 63 semantic
  entries have reader/writer and lifetime rows. The independent WP3 join contains
  134 domain rows: 36 campaign-state scalars, 62 typed record fields, and all 36
  decoded dispatch selectors, each with consumers or a structured bounded reason.
- **WP4:** `jr`: 36 tables, 45 computed code jumps, 14 reason-bounded unresolved;
  `jalr`: 99 global callback uses, 36 record-field calls, 4 reason-bounded unresolved.
- **WP5/WP6:** 8 record views cover object/contact/enemy/projectile/seed/plant/player/
  camera/render/audio/objective/frontend; 181/524 bytes typed, and every remaining
  byte explicit. Each family has a five-part ownership model or the frontend's
  structured lifecycle blocker. Training plus all 15 campaign stages were measured.
- **WP7:** all 15 table scenes plus Training's `0x8001AFB0[16] -> 0x8003CFC4`
  resident/shared route, hash-pinned assets, and entry/exit/overwrite ownership.
- **WP8:** an exhaustive 1,112-function caller/callee report, the 63-entry
  reader/writer report, and exhaustive provenance for 327 staged assets across all
  12 required roles.
- **WP9:** an eleven-row ledger checks disassembly, C, runtime, asset observations,
  schemas, registries, generated artifacts, debugger toolchain/source, Canon, and
  roadmap prose. Every row is reconciled or carries an explicit bounded residual.

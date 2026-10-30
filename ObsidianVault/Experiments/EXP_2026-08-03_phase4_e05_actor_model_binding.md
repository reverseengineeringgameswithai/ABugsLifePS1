---
type: experiment
status: complete
date: 2026-08-03
system: actor models and animation
phase: 4
artifacts:
  - analysis/phase4_e05_model_binding_static.json
  - analysis/phase4_e05_model_pointers_live.json
  - tools/phase4_e05_model_binding_extract.py
  - tools/phase4_e05_live_model_pointers.py
  - tests/test_phase4_e05.py
---

# Phase 4 E05 actor→model binding: the table is code, and the registry is 0x800A6300

## Question

E05's `next` asked: "Dump actor model pointers per chunk-31 type at load; build
the type→model table." Where does the game bind chunk-31 actor ids to model
assets, and where do the loaded model pointers live at runtime?

## Answer (short)

The binding is **code, not data**: `level_load_chunks` (0x8005DAD0) walks the
64-slot actor pool at 0x8009FD80 (stride 0x84), reads each record's id (+0x00),
and for ids 1..41 dispatches through the jr table at **0x8001BBDC**, whose case
bodies hardcode the model path string (a0) and the model id (a3 == actor id).
`level_chunk_loader` (0x8005D654) persists each loaded model's pointer at
**0x800A6300 + 4*id** under a first-load guard (`sw v0,25344($at)`, verified in
`asm/hand_written/8005d654_sub_8005d654.s`). The full 41-entry id→path table is
in `analysis/phase4_e05_model_binding_static.json`, decoded from the pristine
EXE with zero consistency problems, and confirmed live on all 16 level saves.

## Method

1. **Synthesis first.** Committed evidence already covered most of the row's
   `missing`: the RCG-005 catalog ([[SYS_actor_model_binding_catalog]], .ALL/.ANM
   grammar round-tripped 78/78 + 58/58 by `tools/parse_all_anm.py`), the plant
   lane (type N → *(0x800A649C+4N) → PLANTNN.ALL), the player anim selector
   machine (0x800A6588/0x800A658A latch), the byte-matched keyframe primitive
   `actor_set_anim_sequence` (0x8004C10C), and the mover-VM op14 `anim_clip_load`
   transition primitive. The phase-3 jr-table decode already held the dispatch
   (site 0x8005DCA0, table 0x8001BBDC, 41 targets) — the row had simply never
   been joined against it.
2. **Static extraction** (`tools/phase4_e05_model_binding_extract.py`): decode
   each case body straight from pristine `SCUS_942.88` (t_addr verified, first
   insn pinned), read the path strings, cross-check case targets against
   committed `analysis/phase3_jr_tables.json`, and join against the committed
   D01 id→species roster. All 17 known species line up with their decoded paths
   (daddy long legs→`chars2\hspider`, mite→`chars3\weevil`, pill→`chars3\protect`,
   wall worm→`chars4\badcent`, …); 23 previously role-unknown ids gain model
   bindings (Dot, Thumper, Thud, Atta, Molt, acorn, soil, …).
3. **Live confirmation** (`tools/phase4_e05_live_model_pointers.py`, isolated
   instance port 23700, config `/tmp/dsrepro-e05-20260803`, pristine disc,
   poll-only loadState+readMemory): all 16 level saves. Asserts per level:
   Flik slot 0 loaded; every pool id has a non-null pointer; all pointers in
   RAM. Result: **16/16 pass**, and the non-null set is *exactly*
   {0} ∪ {pool ids} ∪ {plant slots 104..117} on every level.

## Findings beyond the named gap

- **Plant unification.** The second dispatch (0x8005E2AC, jr table 0x8001BC84,
  14 entries, list built by 0x80052090) loads `plants\plantNN` with a3 = 103+N —
  so the Canon plant model table 0x800A649C+4N **is** slots 104..117 of the same
  0x800A6300 registry. One mechanism, two lanes.
- **Flik variants are scene-keyed** at 0x8005DB64..0x8005DC74 via [0x80082504]:
  scenes {2,3}→`chars3\flickd`, {4,5}→`chars4\flickp`, {6,10,11,14}→`chars3\flickp`,
  else `chars\flick` (slot 0, a3=0). Live scene words ground the sets: council=2,
  tunnels=3, city=4/5, cliffside=6 (matches C15's committed "scene-6"),
  clover=7, riverbed_flight=8, anthill_two=9, riverbed=10, birdnest=11, tree=12,
  arena=13, bug_bar=14, showdown=15, anthill=1, training=17.
- **id 11 = the seed actor** (`bits\seed`), the only table-1 case with a
  dedicated loader (0x8005D924), and the catalog's one model with no .ANM.
  This corrects D01's working name for id 11 ("ambient critter / large beetle"):
  D01's *structural* finding stands (flag-excluded from quota and homing — a
  non-enemy), but the actor is the plantable seed. A12's independent census
  ("id-11 seeds", uncommitted at time of writing) concurs.
- **Skeleton bank base resolved.** The prologue memsets **0x80089F58 for
  25,200 bytes = 300 × 84-byte bone records** at level load. This reconciles
  [[MEM_8008A1F8_Skeleton_bone_transform_8008A1F8]] (bank at +8 records) with
  the grammar page's 0x80089F58 claim — both were right; one bank.
- **Second per-id registry 0x800A2188 — role OPEN.** Consulted by the loader on
  the first-load path (`lw a3,8584($at)`). Live, campaign-wide: wherever
  non-null it *equals* the model pointer; null for id 11 (seed) everywhere and
  for slot 0 (Flik) on scenes {4,5,7,9,12} — the Flik nulls don't correlate
  with the variant sets, so "animated models only" does not explain it. Writer
  unattributed. Named probe if ever needed: write-watch 0x800A2188 across one
  Interpreter-mode level load.
- **Death-anim dispatch located.** The 12 static-named setters
  0x80049A58..0x80049B60 are the targets of jr table **0x8001B1D4** inside
  `enemy_update_deathanim` (committed phase-3 decode) — per-species death-anim
  variants, not an unknown state machine.

## Gates

`tests/test_phase4_e05.py` — 7 tests: EXE pin + zero consistency problems;
table-1 completeness/self-consistency (41 rows, a3==id==slot, seed special
case); plant window arithmetic (identity with the Canon table); curated
species↔path joins; extractor regeneration determinism; 16/16 live exactness
(set arithmetic per level); scene-word cross-checks. All pass.

## Related

[[SYS_actor_model_loading]] · [[SYS_actor_model_binding_catalog]] ·
[[MEM_8009FD80_enemy_actor_pool]] · [[MEM_8008A1F8_Skeleton_bone_transform_8008A1F8]] ·
[[FUNC_8005DE60_load_character_models]] · [[Seed_plant_output_binding]]

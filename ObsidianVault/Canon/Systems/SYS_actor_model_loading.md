---
kind: system
id: SYS_actor_model_loading
created: 2026-08-03
updated: 2026-08-03
status: runtime_confirmed
confidence: confirmed
source_state: original_game
address: 0x8005DAD0
src_paths:
  - tools/phase4_e05_model_binding_extract.py
  - tools/phase4_e05_live_model_pointers.py
patch_policy: safe_to_read
---

# SYS_actor_model_loading — id→model dispatch and the runtime pointer registry

## Law

The actor→model binding is **code, not a data table**. At level load,
`level_load_chunks` (0x8005DAD0) walks the 64-slot actor pool at `0x8009FD80`
(stride 0x84), reads each record's id (+0x00), and for ids **1..41** dispatches
through the jr table at **0x8001BBDC** (index = id−1). Each case hardcodes
`a0 = model path string` (pool at 0x8001B87C+) and `a3 = model id == actor id`,
then tail-calls `level_chunk_loader` (0x8005D654), which under a first-load
guard persists the loaded model's pointer at:

> **`0x800A6300 + 4*id` — the per-id model pointer registry (128 slots).**

Verified byte-level in `asm/hand_written/8005d654_sub_8005d654.s`
(`sw v0,25344($at)`, `$at = 0x800A0000 + id*4`) and live on **all 16 level
saves**: the non-null slot set is *exactly* {0 (Flik)} ∪ {this level's pool
ids} ∪ {this level's plant slots} on every level
(`analysis/phase4_e05_model_pointers_live.json`).

## The full id→path table

Decoded from pristine `SCUS_942.88`, zero consistency problems, cross-checked
against the committed phase-3 jr-table decode and the committed D01 id→species
roster (all 17 known species match): see
`analysis/phase4_e05_model_binding_static.json` (`table1_actor_models`).
Highlights: 6 `chars\fly`, 9 `chars\badbug`, 10 `chars\mos`, **11 `bits\seed`**
(the only case with a dedicated loader, 0x8005D924), 12 `chars\grub`,
13 `chars\wasp`, 14 `chars2\dot`, 15 `chars2\ggrassh`, 16 `chars2\thumper`,
17 `chars2\hspider`, 18 `chars2\taxibug`, 19 `chars2\roach`, 22 `chars2\hopper`,
28 `chars3\atta`, 29 `chars3\molt`, 30 `chars3\bbird`, 34 `chars3\dragfly`,
35 `chars3\flikharv`, 36 `chars3\thud`, 37 `chars3\weevil`, 39 `chars3\protect`,
40 `chars4\badworm`, 41 `chars4\badcent`.

## Plant lane unification

A second dispatch (0x8005E2AC, jr table **0x8001BC84**, 14 entries, per-level
list built by 0x80052090) loads `plants\plantNN` with `a3 = 103+N`. Therefore
the Canon plant model table `0x800A649C + 4*N` ([[Seed_plant_output_binding]])
**is slots 104..117 of the same 0x800A6300 registry** — one mechanism, two
lanes.

## Flik variants (scene-keyed, slot 0)

Pre-dispatch at 0x8005DB64..0x8005DC74 selects the player model by the scene
word `[0x80082504]`, loading it with `a3 = 0` (slot 0): scenes {2,3} →
`chars3\flickd`; {4,5} → `chars4\flickp`; {6,10,11,14} → `chars3\flickp`;
otherwise `chars\flick`. Live scene words per stage are in the live artifact
(training=17, anthill=1, council=2, tunnels=3, city=4/5, cliffside=6,
clover=7, riverbed_flight=8, anthill_two=9, riverbed=10, birdnest=11, tree=12,
arena=13, bug_bar=14, showdown=15). The harvester Flik (`chars3\flikharv`)
loads as pool actor id 35, not via this pre-dispatch.

## Skeleton bank

The prologue memsets **0x80089F58, 25,200 bytes = 300 × 84-byte bone records**
at every level load. [[MEM_8008A1F8_Skeleton_bone_transform_8008A1F8]] (bank at
base+8 records) and the grammar page's 0x80089F58 base are the same bank.
After each plant load, the case code reads the model header's s16 at +4 and
writes into that bank record's +0x24/+0x20 (skeleton slot linkage).

## Open residual (explicit)

`0x800A2188 + 4*id` is a second per-id registry the loader consults on the
first-load path. Live, campaign-wide: wherever non-null it **equals** the model
pointer; null for id 11 (seed, the corpus's one .ANM-less model) everywhere,
and null for slot 0 (Flik) on scenes {4,5,7,9,12} — which defeats a naive
"animated models only" reading. Writer unattributed; role OPEN. Named probe:
write-watch 0x800A2188 across one Interpreter-mode level load.

## Corrections (2026-08-03)

- E05's registry row previously bound "actor skinned update 0x800563D4" — per
  its own Canon page that function is the **per-frame player animation
  selector**, not a generic skinned-mesh update.
- D01's working name for id 11 ("ambient critter / large beetle") — the model
  binding (`bits\seed`, dedicated loader) identifies it as the **seed actor**;
  D01's structural finding (flag-excluded from quota/homing, non-enemy) stands.

## Evidence

- `analysis/phase4_e05_model_binding_static.json` (EXE-decoded; exe sha256 pinned)
- `analysis/phase4_e05_model_pointers_live.json` (16/16 levels, poll-only)
- `tests/test_phase4_e05.py` (7 gates, all passing)
- [[EXP_2026-08-03_phase4_e05_actor_model_binding]]

## Related

[[SYS_actor_model_binding_catalog]] · [[MEM_8009FD80_enemy_actor_pool]] ·
[[FUNC_8005DE60_load_character_models]] · [[FUNC_800563D4_actor_skinned_update]]

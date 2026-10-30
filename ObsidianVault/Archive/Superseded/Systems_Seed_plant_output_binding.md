---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Seed plant output binding.md
aliases:
  - "Seed plant output binding"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Seed plant output binding.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Seed_plant_output_binding.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Seed plant output binding (HRE-004)
type: system
status: solved (runtime + static, LEVEL01 fixture)
updated: 2026-07-02
confidence: CONFIRMED (matrix, spawner, model binding, override byte); LIKELY (purple berry-grant kind ids)
tags: [system, seed, plant, powerup, gameplay, hre-004, leveleditor]
---

# Seed → plant output binding (HRE-004)

> [!warning] Canon routing
> Current seed/plant Canon is [[SYS_seed_plant_behaviors]]. If this note is used near berry color or descriptor work, route descriptor-safety decisions through [[SYS_berry_pickup_render_descriptors]] and [[HOOK_forbidden_patch_ranges]] first.

> Closes the **HRE-004** "full seed/plant output binding" hard-RE task from
> [[Retail Gameplay Completeness Gap Audit]]: the complete, engine-level chain from
> **token pickup → seed color/count → plant type → PLANTxx.ALL model → interaction handler**,
> proven live on LEVEL01 (fixture `SCUS-94288_8.sav`, isolated DuckStation port 23460,
> pristine v1.0 disc, fork rev `fe0cca1`).

## The selection law (CONFIRMED, disassembled + live-swept)

Plant spawner **`FUNC_8005BDBC(seed_actor)`**:

```
record   = *(seed_actor + 0x80)              // runtime seed record (from LEVEL.RAW chunk 31)
override = record[+0xF]                      // packed per-seed plant override
if (override != 0)
    idx = (override & 0xF) * 4 + (override >> 4)      // low nibble = color, high = count-1
else
    color = record[+0xE]                              // 0..4
    count = counters[0x800A6598 + color] >> 4         // stored n*17, high nibble = n
    idx   = color*4 + count - 1                       // linear 0..19

(type, extra) = u16 pair @ 0x8007A448 + idx*4         // THE binding table (EXE-resident)
```

- **Token counters are contiguous**: `0x800A6598..9C` = orange/blue/green/0x2C/0x2D lanes
  (kinds `0x29..0x2D`), stored as `n*17` (see [[Grain emblem and HUD total mod]] / pickup handlers).
- **Override byte live-CONFIRMED**: poking runtime `record+0xF = 0x30` spawned type 2 (cannon)
  while the counters would have given type 5. Authored seeds can force any plant.
- Special case: `scene_id == 0x11` with actor `0x8009FE04` → clears `0x8009FE66` and returns
  (a special/tutorial seed path, not decoded further).

## The full 20-entry matrix (0x8007A448, dumped + all 20 live-verified)

| lane (color idx) | token kind | counter | ×1 | ×2 | ×3 | ×4 |
|---|---|---|---|---|---|---|
| 0 brown/orange | 0x29 | 0x800A6598 | **5** mushroom trampoline | **3** propeller plant | **8** dandelion | **2** cannon plant |
| 1 blue | 0x2A | 0x800A6599 | **7**/0x2000 invincibility | **7**/0x3000 health | **6**/0x0000 bubble shield | **7**/0x4000 super jump |
| 2 green | 0x2B | 0x800A659A | **4** small leaf platform | **10** taller leaf platform | **9** 3-leaf climber | **1** rose/4-leaf climber |
| 3 purple | 0x2C | 0x800A659B | **6**/0x4000 | **6**/0x2000 | **6**/0x1000 | **6**/0x3000 |
| 4 yellow | 0x2D | 0x800A659C | **14** blue-berry shooter | **13** purple-berry shooter | **11** mine plant | **11** mine plant (dup) |

This matches the operator-supplied retail matrix in [[Retail Gameplay Completeness Gap Audit]]
row-for-row, including "no fourth yellow plant" (type 11 duplicated). Bold = plant **type**;
`/0xNNNN` = the `extra` halfword (`0x8007A44A + idx*4`, stored to slot `+0x2E`).

**Visual confirmation** (grow-and-screenshot sweep): types 2,3,4,5,6 (berry cluster AND bubble),
7 (red fruit plant, one model for all three effects), 8, 9, 10 confirmed on-screen in LEVEL01.
Types 1, 11, 13, 14 spawned *functioning but invisible* actors — their models are **not loaded
in LEVEL01** (see model table below); type 14 demonstrably fired blue berries with no body.

## Plant slots (runtime)

- **20 slots × 0x30 bytes @ `0x80090BF0`**, cursor `0x800822B8` (wraps at 0x14, skips occupied).
- Slot layout: `+0` s16 type · `+2` s16 (data word2) · `+4` (anim byte<<16) · `+8/+C/+10` X/Y/Z
  (Y = seedY − 0x4000, or − 0x4800 for rooted seeds `seed+0x40==3`) · `+0x18` anim-seq ptr ·
  `+0x1C` data cursor · `+0x20` **seed actor back-pointer** · `+0x26` s16 (data word0) ·
  `+0x2E` u16 = `extra` | runtime state (bit2 = mature/visible, bit3 = berry-spawned, low bits = phase).
- Per-type growth-anim data blocks: ptr table `0x8007A40C + type*4` (types 0..14; frame-sequence
  scripts at `0x8007A0B0..`).

## Natural trigger path (jump-on-seed)

Seed actor update (caller **`0x8004D4E0`**; wrapper `0x8005BD58`): jump-on-seed sets actor flag
**`+0x5C` bit 0x20** + sink timer **`+0x6C`**; while timer>0 the seed sinks (`Y += 0x800`/frame)
with dirt-puff pieces (`contact_alloc` ctor `[0x800910A3]+0x1B`); at timer 0 it calls the spawner,
then writes the seed's new position back into its record (`record[+0xD]==0` gate). `+0x62` is set
to 0x2710 (re-plant cooldown). Forcing `+0x5C|=0x20, +0x6C=2` reproduces planting deterministically
(this is how the 20-combo sweep was driven). A bare `debugger.callFunction(0x8005BDBC)` fills the
slot but nothing animates it — growth/render are driven off the seed-actor state, not the slot alone.

## Model binding: type N ↔ PLANTNN.ALL (CONFIRMED)

- Renderer (reads slot type @`0x80021354..`): model ptr = **`*(0x800A649C + type*4)`** —
  a per-level table populated at level load; NULL when that plant isn't in the level's manifest.
- **LEVEL01 loads types 2–10 only**, in memory order 5,7,4,10,9,3,8,2,6; types 1,11,12,13,14 = NULL.
- File identity proven by RAM adjacency: each `type-N header + anim block + PLANTNN.ALL image`
  region chains end-to-end (image end + 8 = next header) and every image's pointer-free vertex
  runs match exactly one `PLANTS*/PLANTNN.ALL` (9/9 loaded types, ≥9/9 chunks each, one ambiguity-free
  base per file).
- EXE filename table `plants\plant01 .. plants2\plant14` @ **`0x8001BAF8`**, stride 0x10
  (indexed `(type-1)*0x10`; no literal pointer refs — computed access).
- **Type 12 (PLANT12.ALL) is unreachable from the token matrix** — only an authored override byte
  can spawn it. Free authoring hook.

## Interaction handlers (mature plants)

> [!success] **Purple ctor → berry map CLOSED (2026-07-03)** → [[Purple seed plant behaviors]]: extra 0x4000→grant 35→equip 1 blue · 0x2000→33→2 homing · 0x1000→32→4 MEGA · 0x3000→34→3 GOLD (all four equip transitions movie-observed). Same grant types 32–35 as the drop system.


> [!success] Brown-lane handler physics + the seed crack/carry/discard lifecycle are now fully decoded (2026-07-03) → [[Brown seed plant behaviors]] + `src_re/brown_seed_plants.c` (trampoline bounce −3328, propeller accelerating lift, dandelion attach, cannon pin+launch −7680; slam-crack trigger `0x8004af80`; discard = instant place-at-feet).


Dispatcher `0x8005BFBC` (slot walker): when `slot+0x2E & 4`, `jr` via table **`0x8001B848`**
indexed `type-2` (types 2..14):

| type | handler | behavior |
|---|---|---|
| 2 | `0x8005C110` | cannon launch |
| 3 | `0x8005C258` | propeller lift |
| 5 | `0x8005C58C` | trampoline bounce |
| 6 | `0x8005C6F0` | **spawns contact object `ctor = (extra>>12) + 0x1F`** at (X, Y−0x1400, Z): extra 0 → ctor 0x1F bubble shield; 0x1000..0x4000 → ctors 0x20..0x23 berry grants; sets slot bit3 (once) |
| 7 | `0x8005C744` | direct effect (gates slot+2==2 && slot+4==0x80000; extra 0x2000/0x3000/0x4000 = invincibility/health/super-jump) |
| 8 | `0x8005C818` | dandelion (carry/glide) |
| 11 | `0x8005C918` | mine |
| 13 | `0x8005CA24` | purple-berry shooter |
| 14 | `0x8005CA7C` | blue-berry shooter |
| 4/9/10/12 | `0x8005CCE8` | passive (platform/climb via collision, no dispatcher verb) |

## Token pickup side (already known, now connected)

`fcn.8003E760(objIndex, level)` (called from token handlers, see
`src_re/pickup_handlers_80054288_80054554.c`) does **NOT** choose the plant — it only re-skins the
pickup sprite descriptor `object_pointer_list 0x80096B98[objIndex]`: `level` into desc`+6` low 2
bits and `level<<6` into the U-coordinate bytes (+8,+0xA..+0x12); odd bytes hold the lane row
(0x00/0x40/0x80/0xC0) — a 4×4 sprite-atlas selector. Lane→objIndex: 0x29→0x16, 0x2A→0x17,
0x2B→0x19, 0x2C→0x18, 0x2D→0x2F.

## Level-editor implications

- **Per-seed color and forced plant are on-disc editable**: LEVEL.RAW **chunk-31** record bytes
  `+0xE` (color lane 0..4) and `+0xF` (override, `(count-1)<<4 | color`) map 1:1 into the runtime
  record (verified for records #19/#26 against `0x80094D10`). The proven chunk-31 edit pipeline
  ([[Seed planting system]]) already covers them.
- Plant availability per level = the level's plant-model manifest (which types have non-NULL
  `0x800A649C` entries). Spawning a type whose model isn't loaded gives a working but invisible
  actor — don't author those without adding the model to the level load set (open: where the
  per-level plant manifest lives on disc).

## Residuals (bounded)

- Purple-lane berry **grant ids**: ctors 0x20..0x23 index metadata table B (`0x8007941C`, stride
  0x14), not pickup-kind space; the exact ctor→berry-kind/marker map (esp. count 3 → ctor 0x20)
  needs one live grab-the-berry check or a table-B row decode.
- Per-level plant **manifest source on disc** (what makes LEVEL01 load types 2–10, and in that order).
- Type-7/6 handler fine detail (SFX ids, effect durations) undecoded.
- Scene-0x11 special seed path.

## Repro

- Fixture `~/.local/share/duckstation/savestates/SCUS-94288_8.sav` (seed A closeup; orange ctr 0x11).
- Isolated instance: `launch_debugger_instance.sh start --disc "Disney-Pixar A Bug's Life (v1.0).cue" --port 23460 --no-fastboot`.
- Sweep: load state → poke `record+0xE`=lane, `0x800A6598+lane`=count·17 → seed actor `+0x5C|=0x20`,
  `+0x6C=2` → advance ~200 frames → read slot @cursor; screenshot. All 20 combos matched `0x8007A448`.

## Related

[[Seed planting system]] · [[Retail Gameplay Completeness Gap Audit]] · [[Berry projectile and homing]] ·
[[LEVEL.DAT object pipeline]] · [[Asset - Character and plant models]] · `src_re/plant_spawn_8005bdbc.c` ·
`src_re/pickup_handlers_80054288_80054554.c`

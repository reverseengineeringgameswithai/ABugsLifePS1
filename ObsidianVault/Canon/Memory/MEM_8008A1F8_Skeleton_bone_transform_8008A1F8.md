---
kind: memory
id: MEM_8008A1F8
aliases: [MEM_8008A1F8, 0x8008a1f8, "MEM - Skeleton bone transform 8008A1F8", "MEM - Skeleton bone transform", MEM_-_Skeleton_bone_transform_8008A1F8]
address: 0x8008A1F8
name: Skeleton_bone_transform_8008A1F8
status: static_seen
confidence: confirmed
source_state: original_game
system: []
read_by: []
written_by: []
related_structs: []
evidence: []
src_paths: []
patch_policy: unknown
---

# MEM_8008A1F8 - Skeleton bone transform 8008A1F8

## Purpose

The runtime **skeleton**: an array of per-bone transform structs that the `.ANM` player [[FUNC_8005EC94]] writes animated rotations into, and that skins the [[Asset - Character and plant models|`.ALL` mesh]]. Decoded live (LEVEL01, `operator_backup`) → [[Finding - Character ALL model format]].

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - Skeleton bone transform 8008A1F8
type: memory-structure
address: 0x8008A1F8
confidence: CONFIRMED
tags: [memory, animation, skeleton, bones, models, b7]
---
# MEM — Skeleton bone-transform array (`0x8008A1F8`)

> The runtime **skeleton**: an array of per-bone transform structs that the `.ANM` player [[FUNC_8005EC94]] writes animated rotations into, and that skins the [[Asset - Character and plant models|`.ALL` mesh]]. Decoded live (LEVEL01, `operator_backup`) → [[Finding - Character ALL model format]].

| Field | Value |
|-------|-------|
| Base | `~0x8008A1F8` (FLICK's skeleton in `operator_backup`) |
| Stride | **84 bytes (`0x54`)** per bone |
| Count | **24 bones** (FLICK; = `.ANM` sub-block `+4`) |
| Next actor | `+42×84` away (observed inter-skeleton stride 3528) |

## Bone struct (84 B) — known fields
- **`+0x00 … +0x13` = 3×3 GTE rotation matrix** (9 s16 packed in 5 words) — loaded via `ctc2 rt_0..rt_4` at `0x800605c4`.
- **`+0x14 / +0x18 / +0x1c` = translation** (TRX/TRY/TRZ) — loaded via `ctc2 trx/try/trz` at `0x800605f4`.
- The animator [[FUNC_8005EC94]] writes interpolated channel values into the `+0x18` region (`sh v1,0x18(a3)`, `+0x1e=1`); an Euler→matrix build step (not yet split) reconciles this with the matrix the GTE reads. GTE-scaled (`4096 = 1.0`); un-animated bone ≈ identity.
- Remaining bytes (`+0x20…+0x54`) = parent-link / flags / scratch — TODO.

## Skinning (uses this struct)
Per bone, the matrix (`+0`) + translation (`+0x14`) are loaded into the GTE; per vertex the skinning emitter `0x80014730` does **`mvmva` (`posedVert = M·V + T`)** — rigid one-bone-per-vertex transform → projected (RTPS) and drawn by [[FUNC_800172DC]].

## Role in the pipeline
1. `.ANM` channel *i* → bone *i* rotation (sparse, bitmask-gated, keyframe-interpolated by frac `t2`).
2. Animator writes the interpolated rotation to `bone[i]+0x18`.
3. Skeleton skins the `.ALL` primitive list, drawn by [[FUNC_800172DC]] (shared `0x8012c` mesh buffer). *(skinning math = residual)*

## Bank base resolved (E05, 2026-08-03)

The bank's true base is **`0x80089F58`**: `level_load_chunks` (0x8005DAD0)
memsets `0x80089F58` for **25,200 bytes = 300 × 84-byte bone records** at every
level load (asm/hand_written/8005dad0_level_load_chunks.s, prologue). This
page's `0x8008A1F8` is `base + 8 records` (FLICK's skeleton as observed in
`operator_backup`), and the grammar page's `0x80089F58` citation for the
crossfade sampler is the same bank — the two bases were never in conflict.
After each plant-model load, the case code at 0x8005E2AC+ reads the model
header's s16 at +4 and writes bank record fields `+0x24`/`+0x20` (slot
linkage). See [[SYS_actor_model_loading]].

## Related
- [[Finding - Character ALL model format]] · [[Asset - Character and plant models]] · [[FUNC_8005EC94]] · [[FUNC_800172DC]] · [[Finding_-_Character_ALL_model_format|character-model format status]] · [[SYS_actor_model_loading]]


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - Skeleton bone transform 8008A1F8.md`
- Migration status: copy-first Canon seed.

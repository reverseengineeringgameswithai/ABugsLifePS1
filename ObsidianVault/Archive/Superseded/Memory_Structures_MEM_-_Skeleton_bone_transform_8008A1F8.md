---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/MEM - Skeleton bone transform 8008A1F8.md
aliases:
  - "MEM - Skeleton bone transform 8008A1F8"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/MEM - Skeleton bone transform 8008A1F8.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/MEM_-_Skeleton_bone_transform_8008A1F8.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

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

## Related
- [[Finding - Character ALL model format]] · [[Asset - Character and plant models]] · [[FUNC_8005EC94]] · [[FUNC_800172DC]] · [[Blocker - Character and plant model formats are unreversed]]

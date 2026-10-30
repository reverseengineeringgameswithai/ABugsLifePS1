---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Core - Camera and Projection.md
aliases:
  - "Core - Camera and Projection"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Core - Camera and Projection.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Core_-_Camera_and_Projection.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Core - Camera and Projection
type: core
updated: 2026-06-22
tags: [core, camera, projection, gte, milestone5, gap-0028]
---

# Core — Camera & Projection (baseline)

> M5 baseline for [[Gap Audit|GAP-0028]] — what's known about the camera/projection model for editor previews + modding, and the named unknowns. **Provenance:** STATIC = reproducible from `SCUS_942.88` disasm + the sym map; **DYNAMIC = local-only** on the dirty DuckStation fork ([[DuckStation Fork Reproducibility]] / GAP-0001), not yet off-machine reproducible.

## Camera state (STATIC — CONFIRMED addresses, provisional semantics)
| Address | Symbol / role | Conf |
|---|---|---|
| `0x1F800374` | `provisional_camera_scratch` (scratchpad) | addr CONFIRMED, name provisional |
| `0x1F800384` | `provisional_view_vector_scratch` | addr CONFIRMED, name provisional |
| `0x1F8003B4` | **`provisional_view_matrix_scratch`** (the per-frame GTE view matrix) | addr CONFIRMED |
| `0x800A0A64` | actor/camera struct — coords `+4/+8/+0xc`, **transform matrix `+0x28..0x3c`** | CONFIRMED ([[Camera]]) |
| `0x80090FB0` | rotation matrix (read by [[FUNC_80025084]]) | CONFIRMED |

The view scratch is loaded into the GTE each frame; the render driver [[FUNC_800224EC]] builds the camera matrix via [[FUNC_80017B98]] (×2) + `fcn.800146e0` (libgte camera leaf), reading `0x1f8003b4/0x1f800384/0x1f800374`. Cull transform = [[FUNC_800140A0]].

## Projection / viewport (STATIC — CONFIRMED)
- Native render **512×224**; near-ground clips off the bottom at `y>200` ([[Camera]]).
- Projection = GTE (COP2) RTPS/RTPT; per-vertex projector = [[FUNC_80010000]] (RTPS `0x800104a8`, RTPT `0x800104d8`, NCLIP `0x800104fc`, SXY store `0x80010718`).
- Two DRAWENVs alternate (draw offsets `(0,256)`/`(512,256)`; clips `(0/512,256,512,240)`) — see [[MEM - OT output buffer pointer 8008240C]].

## Follow-law (DECODED + validated 2026-06-22 — GAP-0028)
4-stage per-frame pipeline: **`fcn.8004df18`** (follow-law core; commits to cam-state struct `0x80095358` @PC `0x8004e8b4`) → `fcn.8004ea8c` (plumb to `0x8009ec50`) → `fcn.80027cbc` (copier/orient → scratchpad C) → [[FUNC_800224EC]] (present; writes scratchpad C/Cdiv/RT @ `0x1f800374`; **live-confirmed writer PCs** `0x800227f4`/`0x80022900`/`0x80027e4c`). `fcn.8004df18` reads the player block `0x800a6500` + the sin table `0x80074970` (×16384).

**Cam-state struct `0x80095358`:** heading θ@+0x20, follow-dist@+0x1e, pitch φ@+0x2a, target C@+0xc, final C@+0.

**Boom / orbit-behind-player target:**
- `a1 = cos(φ)·dist`  (pitch tilts the boom arm)
- `tgtX = playerX − (trig(θ)·a1) >> 9`
- `tgtZ = playerZ − (trig(θ+1024)·a1) >> 9`
- `tgtY = playerY − 32·sin(φ)·dist − 512 − HEIGHT`
- **Smoothing:** `C += (target − C) >> 3`  → **k = 1/8** per axis (PCs `0x8004e890/89c/8a4`).
- **Constants (LEVEL01 normal mode):** behind `dist = 900` (×32 = 28,800 world; clamp 350–3000); `HEIGHT = 12288` (mode-selected 4096/12288/24576). The `>>9` scale = the ×32 runtime↔editor unit ratio.
- Heading θ chases `atan2(player − C)` (`fcn.80060ae4`, step-limited); RT (orientation) is built from the cam's own θ/φ, not a runtime look-at; secondary look damping at `0x80090fb0` uses `0x66666667` (×0.4).

**Validation (held-out, one-step predict C from player, `level01.sav`):** **0 error on phase-aligned frames**; ≤114 world (~3.6 editor units) straight, ≤66 turning — confirms the trig θ-dependence. *Dynamic/local-only on the fork (GAP-0001 reproducible).*

## Relationship to model→world + chunk-34 (DEPENDENCY on GAP-0023)
Object-0's master mesh (chunk-34 def + chunk-35 payload, [[Asset - Chunk 34 Master Mesh]]) is the world-geometry layer this transform places. *(The **walkable floor** itself is LEVEL.DAT via [[FUNC_80010000]] — the chunk-35 terrain mesh renders occluded, [[Gap Audit|GAP-0011]]; chunk-34/35's on-screen contribution is the open GAP-0023 question.)* **The world transform is NOT in the chunk** — applied at draw time by the GTE. The editor uses an empirical **`WORLD_PAYLOAD_Y_OFFSET = 1450`**; the true runtime origin is the GAP-0023 carry-forward. Model→world scale (DYNAMIC/local-only, RTPT `0x80017464`): **Y = 1.000**, X 1.569, Z 1.046. **Camera/projection calibration depends on resolving the chunk-34 world-origin** ([[Gap Audit|GAP-0023]]).

## Named missing variables
1. ~~Camera follow/track law~~ **DECODED 2026-06-22** (`fcn.8004df18`; see Follow-law section). Residual for *byte-exact viewport*: closed-form heading/pitch (atan2 step-limiter `fcn.80060ae4`), the collision/LOS boom pull-in (`0x800376a0`/`0x8003633c`), the full RT→GTE projection chain, and non-normal camera modes.
2. **World translation/origin `WORLD_PAYLOAD_Y_OFFSET`** — runtime value vs the editor's `1450` (carry-forward GAP-0023).
3. **Byte-exact horizontal viewport→pixel mapping** ([[Open Questions]] P3 #10).

## Confidence ledger
- Camera state addresses, projection res, GTE projector — **CONFIRMED (static)**.
- Provisional semantic names on the scratch matrices — **LIKELY** (flagged in [[MEM - Global memory map]]).
- "Camera tracks Flik Y + yaws," scale norms — **LIKELY (local-only)**.
- Follow-law formula — **DECODED + validated (2026-06-22, local-only)**: `fcn.8004df18` boom/orbit + smoothing k=1/8; C predicted from player within ~2–4 editor units.

## Next experiments (local-only — cite fork state)
1. `accessLog.lastWriter` / `execTrace` the writer of `0x1f8003b4` / `0x800a0a64+0x28` → derive the follow law; correlate to `player_y` (`0x800a6504`).
2. At a draw-PC pause, read the pure view matrix + a known world point → calibrate model↔screen (also closes GAP-0023 world-origin).
3. Record fixture/frame/PC/observed-output + fork commit `296955321` per [[DuckStation Fork Reproducibility]]; label local-only.

## Related
[[Camera]] · [[Asset - Chunk 34 Master Mesh]] · [[Core - Rendering OT and GPU Packets]] · [[FUNC_800224EC]] · [[FUNC_80010000]] · [[API - camera transform]] · [[API - GTE state]] · [[MEM - Global memory map]] · [[DuckStation Fork Reproducibility]]

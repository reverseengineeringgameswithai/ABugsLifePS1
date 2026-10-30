---
kind: function
id: FUNC_800313A8
aliases: [FUNC_800313A8, 0x800313a8, collision_grid_builder]
created: 2026-07-08
updated: 2026-07-08
name: collision_grid_builder
status: static_seen
confidence: medium
source_state: original_game_reference_or_mod_reference
evidence:
  - src_re/collision_grid_builder_800313a8.c
src_paths:
  - src_re/collision_grid_builder_800313a8.c
address: 0x800313a8
patch_policy: safe_to_read
---

# FUNC_800313A8_collision_grid_builder - collision grid builder 800313a8

## Purpose

This page closes the migration source-coverage gap for `src_re/collision_grid_builder_800313a8.c`. It records the symbol `collision_grid_builder_800313a8` and links the C reference into the structured vault.

- Address if known: `0x800313a8`
- Coverage comments: none


## C source excerpt

Source: `src_re/collision_grid_builder_800313a8.c`

```c
/*
 * collision_grid_builder_800313a8.c — the load-time collision grid/list builder,
 * its ARENA-TOP SCRATCH WINDOWS, and the P51 root fix for the P18–P50
 * replacement-layout faults.  (RE 2026-07-07, live DuckStation + static disasm.)
 *
 * ============================================================================
 * FUNCTION MAP
 * ============================================================================
 * FUNC_800313A8..0x8003229C  collision grid/list builder ("the builder").
 *   Called from the level-load finalizer at 0x8003D5A4 (jal 0x800313A8),
 *   i.e. AFTER the DAT parse builds the render/cull object nodes.  Runs once
 *   per level load (observed at movie frame ~4283 on the boot movie).
 *   Pass 1 writes each sector's world AABB into the runtime sector table
 *   0x800A7E48 (+0x14/+0x1C min, +0x24/+0x28 ext); grid step =
 *   sqrt(Xspan*Zspan*10/N) via the GTE-lzc sqrt helper 0x80060154 (NOT an
 *   allocator — mtc2/mfc2 leading-zero-count + table at 0x8007A4C4/0x8007A658);
 *   cells @0x800B2540 (stride 0x14), member lists @0x800A2388.  [gp+0x508]
 *   (=0x800822A0) = sector count (LEVEL01: 223).
 *
 * 0x8003C2F4                 sw v0,0x4a0(gp) — the only statically resolved
 *   direct writer of arena-limit global [0x80082238] (gp=0x80081D98, so
 *   gp+0x4A0). Value is the hard-coded constant 0x801CC390 (lui 0x801d; addiu
 *   v0,v0,-0x3c70), set in the boot/loader path. The general census also resolves
 *   two readers, while retaining 12,956 unresolved-base accesses (105 same-width
 *   sites in related functions) and 149 unresolved indirect calls.
 *
 *   CORRECTION HISTORY (2026-08-04 audit): “the ONLY writer” exceeded that
 *   residual and is retracted. A separate fixed-form materialisation scan finds
 *   14 sites total, including 0x8003C2F0 itself — so the former “14 other sites”
 *   count was off by one. There are 13 other resolved fixed-form materialisations;
 *   that encoding census is not pointer closure.
 *
 * 0x8003D5D8                 the game's own arena-overflow check right after
 *   the builder call: `if ([0x80082238] < heap_probe) [gp+0x754] = 2`.  It
 *   guards the LIMIT only — NOT the scratch windows below it (the design
 *   assumed level data never grows near the limit).
 *
 * ============================================================================
 * THE SCRATCH WINDOWS (the P18–P50 fault mechanism)
 * ============================================================================
 * At entry the builder carves FIVE per-sector scratch arrays (stride 4,
 * indexed by sector) at fixed negative offsets below the arena limit:
 *
 *   0x800313B4  lui  v0,0x8008
 *   0x800313B8  lw   v0,0x2238(v0)     ; v0 = [0x80082238] = 0x801CC390
 *   0x800313E8  addiu s7,v0,-0x1000    ; array A (sp+0x58)
 *   0x800313EC  addiu t8,v0,-0x3000    ; array B (sp+0x60)  minX bounds
 *   0x800313F4  addiu s7,v0,-0x5000    ; array C (sp+0x68)  maxX bounds
 *   0x800313F8  addiu v0,v0,-0x7000    ; array D (sp+0x70)  minZ bounds
 *   0x80031400  addiu t8,v0,-0x2000    ; array E = limit-0x9000 (sp+0x78) maxZ
 *
 * Pristine window = [limit-0x9000, limit) with 0x2000 spacing (2048 sectors
 * per array — far beyond any real level; LEVEL01 uses 223 => only the first
 * 0x37C bytes of each window are written).  Per-group bounds math (the sw at
 * 0x800319A0 init / 0x80031A64 max-update) writes values like
 *   v0 = ((s16[group+8] + s16[group+0xA]) << 5) + runtime_sector.origin_z
 * which are LARGE NEGATIVE for far sectors (0xFFFABFA0, 0xFFF94040, ...).
 *
 * FAULT: render/cull object nodes + render-driver records are heap-allocated
 * UPWARD and, in pristine layouts, end BELOW limit-0x9000.  A grown chunk-32
 * (authored replacement blocks) pushes live nodes INTO the window; the builder
 * then runs (after node build) and overwrites node/record fields with bounds:
 *   - P20/P22/P23: key-65 payload-holder slot 0x801C362C := 0xFFFABFA0 (maxZ
 *     array, limit-0x9000 window) -> data bus error at 0x8001EB3C.
 *   - P49: render-driver active record 0x801C561C span := 0xFFF94040 (minZ
 *     array, limit-0x7000 window) -> helper 0x8003EFC8 traversal never
 *     returns (loop 0x8003F290..0x8003F2BC), FUNC_80010000 = 0.
 * Both P-milestone failure signatures are THIS one bug; which structure lands
 * in a written stripe decides the symptom, which is why P18/P25/P26 saw
 * baffling combination-dependent pass/fail sets (92 vs 91+92 etc.).
 *
 * ============================================================================
 * P51 FIX — pack the windows (5-word EXE patch, opt-in --p51-scratch-pack)
 * ============================================================================
 * The arrays only need count*4 bytes (223*4=0x37C).  Packing the spacing
 * 0x2000 -> 0x800 moves the scratch floor limit-0x9000 -> limit-0x2800 and
 * reclaims 26 KB of safe headroom; each array still holds 512 sectors (the
 * runtime sector table's BSS budget caps real counts far below that).
 *
 *   0x800313E8: 0x2457F000 -> 0x2457F800   (-0x1000 -> -0x800)
 *   0x800313EC: 0x2458D000 -> 0x2458F000   (-0x3000 -> -0x1000)
 *   0x800313F4: 0x2457B000 -> 0x2457E800   (-0x5000 -> -0x1800)
 *   0x800313F8: 0x24429000 -> 0x2442E000   (-0x7000 -> -0x2000)
 *   0x80031400: 0x2458E000 -> 0x2458F800   (-0x2000 -> -0x800, rel. shifted v0)
 *
 * Implemented in tools/build_g3_native.py apply_p51_scratch_window_pack()
 * (P51_SCRATCH_SITES), baked into the staged EXE with strict original-word
 * verification.  Strictly safer for pristine content: the packed window is a
 * SUBSET of the region the pristine builder already scribbled, and pristine
 * levels were laid out to stay below limit-0x9000 anyway.
 *
 * NOTE — spacing 0x1000 was tried first and is NOT enough: the full 13-sector
 * envelope's node/record top crosses limit-0x5000 and the P27 helper-loop
 * signature returns.  0x800 clears every validated layout.
 *
 * ============================================================================
 * VALIDATION (cold boot, movie replay, no P24 guard)
 * ============================================================================
 * - Full 13-sector envelope [0,73,87,88,89,90,91,92,93,99,100,107,108] — the
 *   P48/P49/P50 hard failure (91+92 together) — PASSES: exact spawn, marker
 *   f4410, goal f4490, RENDER_C=0, FUNC_80010000=673, no plunge.
 *   Disc build/ABL_g3native_p51_full_envelope.
 * - Minimal-fail set [0,73,92]+seed PASSES (build/ABL_g3native_p51_minimal_0_73_92).
 * - 2x2 matrix closed: neither=fail (P19), P24-guard-only=fail (P48),
 *   pack-only(0x800)=PASS, guard now unnecessary for these layouts.
 * - P11 baseline WITHOUT the flag: staged EXE byte-identical to the frozen
 *   baseline (sha256 185861a9...) — no default behavior change.
 *
 * ============================================================================
 * P52 — FULL AUTHORED COLLISION WORLD (unlocked by P51)
 * ============================================================================
 * tools/build_g3_native.py --replace-all-blocks --replace-tile-n 8: every
 * selected corridor block sector (86) gets a fresh authored mesh block
 * (emit_floor_planes replace path), on top of the 85 authored flat-sector
 * add-blocks => 171/189 chunk-32 sectors fully authored,
 * flattened_old_block_retained_footprints = 0 (the P15 "not a clean authored
 * collision world" core count closes).  At tile_n=8 the world chunk-32 is
 * SMALLER than pristine (0x386F0 vs 0x39D90) — strictly safe layout.
 * Cold boot: Flik spawns, walks, marker+goal fire; render live (walk
 * screenshots build/p52_world_walk_*.png).  Remaining non-authored: 11
 * malformed relocation-region sectors 178–188 (native oddballs, excluded by
 * decoder) + 7 outside-region sectors.
 *
 * CAVEAT (documented, not a disc defect): heavy execTrace instrumentation
 * armed around the load/spawn window can perturb frame timing enough to trip
 * the P26/P27 render-driver record race on world-scale discs (same bytes pass
 * uninstrumented and complete goal).  Validate world-scale discs with
 * captureFrame liveness + flag probes; arm execTrace watches only for
 * layout-envelope discs (13-sector class), where they are proven stable.
 */
```

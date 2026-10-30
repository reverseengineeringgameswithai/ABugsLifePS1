---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Tier 3 - GTE Render Path.md
aliases:
  - "Tier 3 - GTE Render Path"
migration_action: split
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Tier 3 - GTE Render Path.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Tier_3_-_GTE_Render_Path.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

# Tier 3 — GTE Render Path (CPU→GTE render rework)

**Goal (from GAP-T3-7):** the Tier-3 custom-level renderer (`mod/caves/tier3_otrender.c`) projects geometry
in **software on the R3000**, which was believed to be the dominant FPS cost that caps level density. This
initiative moved the render pipeline toward the **GTE (COP2) hardware path** the native game uses, to raise the
triangle budget for dense authored terrain (subtle "bumpy" floors) at a steady 30 fps.

Plan file: `~/.claude/plans/steady-stargazing-coral.md`. Auto-memory: `tier3-gte-render-path`.
Related: [[Tier 3 - Custom Level Engine]] (GAP-T3-7 section), [[Core - Camera and Projection]].

## Status (2026-07-04)

Two renderer changes landed, **both proven correct (pixel-identical frame, cold-boots clean)**, but the FPS
payoff is **smaller than hoped** — the software transform was NOT the real bottleneck, and no single stage is.

| Change | Correctness | Measured render-cost impact* |
|---|---|---|
| Phase 1 — GTE vertex transform | frame pixel-identical, cold-boots | **~0.6%** (transform was ~2% of hook) |
| GPU-scissor (drop 4-plane software screen clip) | frame pixel-identical, cold-boots | **~9%** |
| (subdivision — measured for reference, unchanged) | — | ~11% of hook |

*measured via `stepOut` cycle-delta across `tier3_otrender_hook` @0x801F0C00 — see the METHODOLOGY CAVEAT below;
treat magnitudes as approximate.

## The proven GTE recipe (Phase 0, live-verified ≤1px vs software)

Inputs already in RAM: world→view rotation `R` (Q12, row-major, **includes the 1.6× camera zoom**,
non-orthonormal) @ `0x80090FB0` (9×int16); camera pos `C` @ `0x1F800374` (3×int32); GTE projection constants
`H=160`, `OFX=256`/`OFY=120` (stored Q16 in GTE cr24/cr25), `ZSF3=341`/`ZSF4=256`. At our hook the camera
matrix is NOT resident in the GTE control regs → we must `ctc2` it in ourselves.

Per-frame: `ctc2` R into GTE control cr0-4 (cr0=R0|R1<<16, cr1=R2|R3<<16, cr2=R4|R5<<16, cr3=R6|R7<<16, cr4=R8),
TR=0 (cr5-7). Per vertex: pre-scale `d=(V-C)>>4` (fits GTE's 16-bit VXYZ regs; same >>4 the software path used);
`mtc2` d.xy→data0, d.z→data1; `.word 0x4a180001` (RTPS, sf=1→>>12). Read `MAC1/2/3` (data25/26/27) for view
coords at SOFTWARE magnitude via `<<4` (SW PV = R·d>>8; GTE MAC = R·d>>12), and `SXY2` (data14) for screen
coords (already clamped to GP0-safe ±1024). Screen matches SW `H·x/z+OF` because the /16 scale cancels in the
ratio. **Safe to borrow the GTE at our hook** (DrawOTag `0x80064618`, after all native COP2 for the frame; the
native engine reloads its matrix per object). GTE compute ops are emitted as `__asm__(".word 0x..")` — gas/armips
have no `rtps` mnemonic; `mtc2/mfc2/ctc2/cfc2` assemble natively. Mind the R3000 GTE load-delay ([[r3000-load-delay-caves]]).

## FILL HYPOTHESIS DISPROVEN (2026-07-04) — it's per-triangle CPU, not fill

Controlled test: flat floor grids covering the SAME footprint (same visible fill area) at different tri
granularity, hook cost measured at the fixed pose (poke synthetic T3LV blob at 0x801F3D00 via
tier3_level_format.MeshBuilder; keep Flik supported — flat grid at Y=-266 IS the collision floor too):
- 2×2 = **8 tris → 23,938 cyc**
- 6×6 = **72 tris → 151,408 cyc**
- 13×13 = **338 tris → 523,831 cyc**

Same area, but cost scales ~LINEARLY with TRIANGLE COUNT (fine = 22× coarse), NOT constant. => the bottleneck is
**per-triangle CPU work (~1,550 cyc/tri), NOT GPU fill.** Dense SMALL tris do NOT help (no texture-cache-locality
win) — they cost dramatically MORE (same fill + way more per-tri CPU). This CORRECTS the earlier "fill-bound"
guess (the flat-vs-textured 18% is a real but minority fill slice; the dominant 82% is per-tri CPU that scales
with count — emit + OT splice + near-clip frac10/lerp10 + loop overhead, spread with no single silver bullet).

**DEFINITIVE CEILING:** ~1,550 cyc/tri, 30fps budget ~1.128M cyc/frame → **~700 tris at 30fps** (minus game
baseline). Neither the GTE path NOR dense-small-tris breaks it. Every incremental CPU optimisation lands ≤18%,
cumulative ≈1.5×. **The ONLY path to native-level density is the ARCHITECTURE PIVOT** — feed geometry through the
native GTE mesh submitter FUNC_80010000, or true-replace — NOT the bolt-on software-OT-insertion renderer. The
incremental-optimisation path (Option 1) is now closed with measured evidence.

**PIVOT TAKEN → [[Tier 3 - Native Terrain Path]]** (2026-07-05): author Blender terrain into `FUNC_80010000` (the
native GTE emitter). M1 done (byte-exact payload codec `tools/native_mesh_codec.py`, 217/217); M2 core done
(authored payload renders through the native emitter, size-preserving). This bolt-on renderer is now **frozen**
as the marginal baseline, not extended.

## Full reliable profile (2026-07-04) — no single lever; likely fill/mix-bound

Measurement FIXED: `stepOut` across the hook @0x801F0C00 is **deterministic to the cycle** at full floor
(523,828 ×3 repeatable). Earlier "unreliable" panic was ONLY the low-nt Flik-fall artifact (thin the floor →
Flik falls → physics-heavy frames pollute the max sample). Anchor pose = `tier3_render_savestate.sav` +
advanceFrames 3. Caveat: the cycle span appears to include concurrent GPU/DMA time (see flat-vs-textured), so
it's wall-clock-ish, not pure CPU — precise CPU/GPU attribution is limited.

Reliable per-stage results at 383-tri spawn vista (hook ~524k cycles):
- GTE **transform** (Phase 1): **0.6%**
- **subdivision**: **6.8%** (35,589 cyc; toggle SPLIT_EXT_LIVE 0x801FE044=0x7FFFFFFF)
- software screen **clip** → GPU scissor: **9%** (54k)
- depth-bucket **LUT**: **~0%** (binary search is free; linear knob DS_MUL_LIVE=251 gave −3 cyc)
- **trivial-accept divides** (Phase 2, GTE screen coords): **0%** — most tris don't trivial-accept here
- **texturing** (flat TEXTURED=0 vs textured): **18%** (94,495 cyc) — the single biggest slice, and it's FILL

Path distribution (383 input tris): ~244 CULLED early (cheap), 50 trivial-accept, 89 near-clip, 14 subdivided,
**136 OT nodes emitted**. Implied ~3,400 cyc per *processed* tri — implausibly high for the CPU ops, which
(with the 18% texturing/fill slice + every CPU optimisation landing ≤9%) says the bottleneck is **GPU FILL /
DMA, not the CPU transform pipeline the GTE path targeted** (consistent with the prior Phase-4h/4i finding
"textured floor drops 30→20fps; big tris blow the fill-timing budget"). Cumulative CPU squeezing ≈ 1.5× at best.

**Bottom line: the GTE/CPU-transform axis was the wrong axis.** The real density lever is FILL — fewer/smaller
textured pixels, better texture-cache locality (which dense SMALL tris actually help), less overdraw — OR a
different architecture (native GTE submitter `FUNC_80010000` / true-replace). Landed changes (transform +
scissor + GTE projection) are all CORRECT (pixel-identical, cold-boot) and a fine baseline, but individually
marginal. **Recommended next: test the fill hypothesis with a real dense-small-tri level (small tris may be
fill-cheaper than the giant sheets measured here), or commit to the architecture pivot.**

## Cost profile — the real finding

Render hook ≈ **1,000–1,500 cycles per TRIANGLE** (clean slope from nt=383→256→128: 548k→362k→236k). At a 30 fps
budget of ~1.128M cycles/frame (2 VSyncs), that caps the renderer at **~several-hundred triangles at 30 fps** —
not "hundreds of dense planes". Crucially the per-tri cost is **NOT concentrated in one stage** (transform 0.6%,
subdivision 11%, screen-clip 9%); the remainder is spread across the perspective **divides**, the depth-bucket
LUT, the 10-word node **emit** + OT splice, the near-plane clip, and per-tri loop overhead. **There is no single
silver-bullet stage** — so the GTE transform swap alone (and even dropping the clip) yields only incremental gains.

Implication: reaching genuinely high density likely needs EITHER cumulative optimisation of every per-tri stage
(GTE projection to kill the divides ~15%, native `otz` for depth, leaner emit — maybe 1.5–2× combined) OR a
different architecture (ride the native GTE mesh submitter `FUNC_80010000`, or true-replace the level), not just
a transform swap. Open design decision.

## METHODOLOGY CAVEAT (important)

Per-hook cycle cost was measured with `debugger.stepOut` across the hook and reading `debugger.status.cycle`.
This is **imperfect**: (1) samples can span a VSync/DMA window (readings cluster near ~1 VSync = 564k cycles),
so small deltas may be noise; (2) at low `ntris` the custom floor vanishes under Flik → he FALLS → physics-heavy
frames pollute the "max" sample (nt=64/16 measured HIGHER than nt=383 — non-physical). Trust only the monotonic
mid-range slope. A reliable next measurement needs paired entry/return breakpoints with clean cycle reads, or the
emulator's true guest present-rate (note: `emulator.getVideoStatus.frame_rate` = display refresh 59.8Hz, NOT the
game's achieved fps; `advanceFrames` runs each frame to completion so it does not expose frame-drops).

## Anchors / repro

- Render-disc gameplay save state = `tier3_render_savestate.sav` (repo root), made on `build/ABL_tier3_render.cue`
  → loadState = live camera + blob@0x801F3D00 (260v/383t) + renderer active. THE anchor for all measurements.
- Cold-boot: movie `flik_to_level01_stall.mv.movie.json` → gameplay ~frame 4265 (COPIED=1, RTPS resident @0x801F0EC4).
- Fast iterate: rebuild cave (`TIER3_KEEP_BLOB=1 python3 tools/build_tier3_render_disc.py`), hot-swap
  `build/cave_otrender.bin` over 0x801F0000 in the loaded SW save state (blob@0x801F3D00 preserved), frame-diff.
- RAM window `0x801F0000..0x801FF000` (~60KB): render code (0x3D00) + blob (0x5100) + PV scratch (0x1E00) +
  NODEBUF (0x3400) + gameplay scratch. ~44KB more free below 0x801F0000 (game OT tops ~0x801E5400) if a
  re-budget is needed.

## Code

`mod/caves/tier3_otrender.c` — GTE transform loop (`ctc2` rotation once/frame + per-vertex `RTPS`, `PVX=MAC1<<4`)
replacing the software matrix-multiply; GPU-scissor clamp (`-1024..1023`) replacing the 4-plane Sutherland-Hodgman
screen clip. Marker/billboard transform loops LEFT on software (few verts, negligible). Depth still uses the
`DS_PVZ` LUT (native-`otz` swap is a pending option).

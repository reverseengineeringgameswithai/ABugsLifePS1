---
kind: experiment
id: EXP_2026_07_11_allmods_spawn_feet_ot_overpaint
name: ALLMODS spawn feet burial — native terrain OT overpaint
status: confirmed_fixed
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mixed_original_and_mod_experiment
related:
  - FUNC_80010000
  - SYS_render_collision_source_separation
  - MOD_g3_local_visual_refinement
  - MOD_g3_native_anchor_alignment
  - PLAYBOOK_mod_regression_troubleshooting
---

# ALLMODS spawn feet burial — native terrain OT overpaint

## Question

Why do Flik's feet appear buried at specific Bigland positions, most visibly
immediately after the LEVEL01 spawn? Is collision locally below the drawn
terrain, or is the visual symptom produced later in the render pipeline?

Operator image SHA-256:
`ad53a7459b2b42a970ca7c855d392b473467a634ac36487249c3d0558e73bd20`.

## Reproduction

Cold-booted `build/ABL_ALLMODS.cue` through the valid ALLMODS fixture
`flik_to_level01_stall.mv.movie.json` (SHA-256
`fa2e81925fbad56af07081fbfe6980f2789a0dd72e6b63b13f9e7b5fc23ed264`).
The fixture ended at movie frame 4253; the captured gameplay frame had:

- player `(X,Y,Z) = (197088,-12704,492896)`;
- `vy=0`, grounded `0x0101`, idle animation `22`;
- authored collision/spawn foot plane `Y-3200 = -15904`;
- containing visual quad height at spawn approximately `-15896.8` runtime.

The 7.2-runtime-unit geometric residual is only about 0.2% of Flik's 3200-unit
body-to-foot offset. A global body-offset or collision-anchor adjustment would
therefore be both disproportionate and wrong for the many positions that already
look correct.

## GPU evidence

At native CRTC foot pixel `(160,183)`, `gpu.pickObject` reported the final visible
contributor as the authored neutral-pebble `GP0(3C)` quad (`tpage 0x660`, CLUT
`0x3FFC`), not Flik. The coarse quad's projected rectangle spanned 169x53 internal
screen units; an adjacent near quad spanned 313x170. They were submitted after
the character in the ordering table and painted over the lower legs.

This is a PS1 primitive-ordering artifact. `FUNC_80010000` submits a complete
terrain primitive to an ordering-table depth; there is no per-pixel modern
Z-buffer to reconcile a large sloped quad against Flik. The artifact appears only
where a coarse custom quad spans the wrong side of the local actor/order boundary.

The solved player/collision assembly was useful as a negative control: the exact
spawn body offset and grounded state were coherent, so no original movement or
collision code patch was indicated.

## Causal A/B

P65's containing floor payload was `0x1B9F0`, with 64 regenerated quads. P66
rebuilt only that registered payload at 12x12 (144 quads), keeping its node anchor,
XZ footprint, sampled surface, coherent pebble material, and registration.

The P66 DAT differs from P65 as follows:

- three changed prefix bytes at `0x4904..0x4906` (the existing 32-bit relocation
  field; its unchanged high byte remains zero);
- one appended/repointed 4348-byte payload;
- no other old-DAT byte changes;
- collision RAW remains byte-identical, SHA-256
  `a406a72d21b1ae6a8c1cd2b3597d4a4cfc743a0be47c8bc5bb9ec3dea8de0d79`.

At the matched cold-boot frame, player position, velocity, grounded state, and
animation were identical. A blue-character pixel mask reached row 469 before and
row 500 after refinement: 31 additional vertical pixels of the feet became
visible. Baseline and fixed frame SHA-256 values were respectively
`d1f7248c33e3f34a37676f9085950cdde6170d7c3d893407ec59ee6e65f8fd5d`
and `2095b357e92825fd42bd5766a199dff131613f713d2fc66daeca437a3885d18f`.

Bounded conclusion: local subdivision fixes the reported spawn artifact by
reducing terrain primitive depth/screen span. It does not change collision or
lift Flik. Other isolated positions can use the same explicit point refinement
after their containing payload is identified; global subdivision is intentionally
avoided because of DAT growth and the per-frame primitive budget.

## Regression results

- ordinary Up, 64 frames: moved normally, remained grounded, animation `0`;
- Up+L2, 60 frames from the same anchor: animation `29`, phase advanced,
  grounded `0x0101`;
- consolidated cold-boot smoke: BOOT/ALIVE/RENDER/WALK all pass;
- `tools/regress_g3_native_authoring.py`: pass, including append/repoint,
  primitive count, surface-height, and shipping-workspace guards.

## Reproducibility and cleanup

- DuckStation fork `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`;
- debugger binary SHA-256
  `08a4720d1afc40f31f6961d3bd21625b17a49463a9c3d18336144e0acc856eab`;
- isolated config `/tmp/dsrepro-feet-p66`, port `23466`, token
  `debugger-1000`, recreated for the fixed image;
- operator profile/instance untouched; owned instance stopped after capture.

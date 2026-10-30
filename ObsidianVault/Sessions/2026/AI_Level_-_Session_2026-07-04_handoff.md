---
kind: session
id: AI_Level_-_Session_2026-07-04_handoff
created: 2026-07-08
updated: 2026-07-08
date: 2026-07-04
status: legacy_imported
legacy_source: ObsidianVault/Systems/AI Level - Session 2026-07-04 handoff.md
aliases:
  - "AI Level - Session 2026-07-04 handoff"
---

# AI Level — 2026-07-04 session handoff

> Migrated from `ObsidianVault/Systems/AI Level - Session 2026-07-04 handoff.md` during the 2026-07-08 vault completion pass. Reason: Chronological/handoff note; keep as history, not Canon.

# AI Level — 2026-07-04 session handoff

> One long bug-fixing session on the operator's playtest reports. **Current playable disc:
> `build/ABL_AILEVEL.cue` (md5 `09d1b80b…`)** — physics stable, pristine-style pebble ground,
> draw-time subdivision, 30 fps. Detailed chronology lives in
> [[AI Level prototype]] (v1→v5 bullets); this note is the *resume-here* summary.

## What got FIXED today (all verified in-game)

| Operator report | Root cause | Fix (where) |
|---|---|---|
| "Shot up in the air at specific things" | Native integrator (`FUNC_8003633C`) commits **garbage resolver output** when Flik is outside the OG sector polygons — one-frame ±20k warps. NOT a floor value (deepen-independent); NOT enemies/springs. | **Teleport guard** in `mod/caves/tier3_walls.c` (1b): Y rising >4000/frame (real jump max ~2816) with last-Y above the death plane → restore last-frame XYZ. `WPREVY @0x801FE038`. |
| "Falls through the floor" | Same bug, opposite sign: `NATIVE_DEEP=1e6` overflowed native plane math (Q12 ceiling ~524287). | `NATIVE_DEEP` back to 40000 + the same guard. |
| "Artifacts that don't look like anything" (brown rectangles) | Billboard tiles: PS1 cutout = **texel index 0**, whose palette color *displays* khaki — tile-audit-by-eyeball lies. Page 0x660 has NO usable sprite except the leaf. | All 4 bprop kinds → leaf cutout (green/brown, per-kind sizes) in `tier3_otrender.c` BPAGE/BCLUT/BU/BV. |
| "Ground looks deformed / not proper dirt" | (a) my E2 window folded the ground's 64×64 **pebble tile** (@(0,192) clut 0x3FFC — the mylevel recipe) onto the 32-px wall tile; (b) one tile stretched per giant face. | Per-CLUT E2 windows (pebble mod-64 / wall-dirt mod-32 / else clear) + exporter wrapped repeat-UVs (`tier3_blender_export.py`). |
| "Ground stretches when walking" | PS1 **affine warp** ∝ triangle size; our sheets are 10-20× pristine polys. Export-side subdivision can't fit the budgets. | **Draw-time adaptive subdivision** in the render cave: near GIANT tris split into 4 (view-space midpoints = perspective-correct), 2 passes, ≤16 sub-tris, zero blob cost. |
| "Stuck at 20 fps" | The v4 split defaults split most of the field; the 30fps frame budget has ~zero slack. | Retuned via live knobs + flip-count instrument: **26k/12k near-limits + 120k extent gate** = split ONLY the giant sheets → 30fps at the worst scene. |
| (found, not reported) | Teleport-guard scratch collided with `DS_MUL_LIVE @0x801FE030` → renderer silently on the linear depth-sort debug path since v3. | `WPREVY` moved to `0x801FE038`. |

## OPEN issues (the pick-up list)

1. **"Can't run forward / berry flies through" (operator repro, unresolved).** Native resolver
   returns ~zero movement at some spots (sector-map-edge behavior); did NOT reproduce on a fresh
   boot of the fixed build — state-dependent. **Operator's exact stuck state saved:**
   scratchpad `user_stuck.sav` (session dir). If it recurs on the new disc: pause there, diff
   against that save. Candidate kill-switch (live-tested OK: walk/jump/hot-spots fine): force the
   integrator's grounded-read `0x80036C38` (`lbu v0,1(s6)`) to `li v0,0` → ALL movement resolves
   via the permissive airborne resolver `FUNC_80035280`.
2. **All-grain emblem at 24/24** — never cleanly observed (test sweeps kept dying to chasers /
   game-overs). One 24/24 state ended input-dead at pc 0xA0. Retest by legitimate collection;
   if it locks, gate the emblem reward (`FUNC_80054EAC` chain) in Tier-3.
3. **Resident mover-VM proximity triggers** (op17/op12, table 0x80077af8) still armed at OG
   coordinates — suspected source of hint/camera input-locks during testing (the Hopper/colony
   FMVs turned out to be GAME OVER cutscenes, so this is demoted, not confirmed).
4. **Ground residuals**: medium tris (45–120k) still un-split (small warp remains); steep
   edge-on faces streak (affine, inherent). Knobs live at `0x801FE03C/40/44` (L0/L1/ext-gate,
   0 = baked 26000/12000/120000) — retune without rebuilds.
5. **Prop art**: everything is leaf cutouts; real mushroom/rock sprites need a VRAM upload
   pipeline (abl_starry GP0 A0 write primitive is the proven building block).
6. **Budgets at ceiling**: render .text `0x2DC0/0x2DF8` (56 B free), blob `20528/20736`
   (208 B free), verts 354/384. Next feature = layout surgery first (candidates: move gameplay
   scratch above 0x801FE048, NODE_MAX trade, FARZ cut).
7. Older work-list items unchanged (bead-chain payload props, depth-LUT peek, telescope
   surplus, Dot leg clipping — see [[AI Level prototype]] §Known quirks).

## Resume kit (hard-won recipes — read before testing)

- **Boot**: full instance relaunch + `movie.load` `flik_to_level01_stall.mv.movie.json` +
  `movie.startPlayback {load_start_state:true}` + 4400 turbo frames. `debugger.reset`+movie =
  black-screen wedge. Movie can end mid-intro (Flik y=2733, input dead) — nudge with up-holds.
- **Teleporting Flik** needs the full grounded reset or he deadlocks input-dead:
  XYZ + `vy=0 @0x800A6530` + `AIR=0 @0x800A6580` + `grounded=0x0101 @0x800A6582` +
  `PREV X/Z/Y @0x801FE000/4/8` + `WPREVY @0x801FE038`. Never teleport into the boxed dead
  space under raised pads.
- **FPS measurement**: count `gpu.getStatus → crtc.vram_source_rect[0]` flips (0↔320, one per
  game frame) per vsync. Walk-speed and position-cadence measures are combat/state-confounded.
  Anchor每 config with `loadState` at a HEAVY scene (spawn vista).
- **Long automated walks**: chasers stun-lock Flik at HP 1 — restore HP `0x800A7E2A` and keep
  runs short/away from enemies.
- **EXE file patching**: `off = vaddr − 0x80010000 + 0x800` (t_addr from the EXE header;
  Ghidra's 0x8000F800 base WRECKS a session if used for restores). `0x80035F24` is
  MID-FUNCTION — never stomp it. `0x80036CD8` = the integrator's normal position COMMIT —
  patching it freezes all movement.
- Codec oracle: `debugger.callFunction 0x8001A1DC(a0=comp, a1=dst)` runs the game's own
  LZ decoder (byte-exact validation of any spliced chunk).

## Related
[[AI Level prototype]] · [[Tier 3 - Custom Level Engine]] · [[Tier 3 - Custom Level Bugs]] ·
auto-memory `tier3-native-pin-and-dat-shifts.md` (same findings, denser)

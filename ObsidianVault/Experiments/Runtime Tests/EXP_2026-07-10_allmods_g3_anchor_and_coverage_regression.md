---
kind: experiment
id: EXP_2026_07_10_allmods_g3_anchor_and_coverage_regression
name: ALLMODS composition audit and G3 visual-collision anchor regression
status: current
created: 2026-07-10
confidence: confirmed
source_state: mixed_original_and_mod_experiment
related:
  - SYS_render_collision_source_separation
  - MOD_g3_native_anchor_alignment
  - PLAYBOOK_mod_regression_troubleshooting
---

# ALLMODS composition audit and G3 visual-collision anchor regression

## Question

Why did the GTE-native authored terrain render away from the walkable collision
world, and is that terrain already present in `build/ABL_ALLMODS`?

## ALLMODS scope audit

Current image:

- `build/ABL_ALLMODS.bin` SHA-256
  `f51cbfd3a4514ad46233206e64a8f79a82a910b99a70a255fd10d54dfe33a5e3`.
- Embedded `LEVEL01/LEVEL.DAT` at LBA 2946 is byte-identical to the staged
  pristine DAT: SHA-256
  `c2ed8f34158470148ef79d96ea74d7fa44035aa7ecf7c261b1cf32293016e71a`.
- Embedded `LEVEL01/LEVEL.RAW` differs because ALLMODS includes the Anthill FLIK
  emblem asset. The manifest does not stage the G3-native terrain/collision pair.

Therefore the current ALLMODS image is the desired composition base, but it does
**not** yet contain the authored GTE-native world. A mismatch seen in the G3 work
cannot be attributed to the current ALLMODS DAT.

The first attempt to test G3 DAT/RAW as DuckStation CD file overlays was rejected
before the experiment ran: the WebSocket request exceeded the current debugger
receive buffer (`Receive buffer overflow`, client reset). The files also exceed
the original ALLMODS ISO extents (`DAT 332824 -> 334012`, `RAW 747748 -> 865558`),
so a whole-file overlay is not a valid composition substitute. No conclusion is
drawn from that failed launch.

## Reproducibility

- Project revision: `e6402e8717f56df37b47405f6423aad0882ed502`, dirty
  operator worktree preserved.
- DuckStation revision:
  `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, dirty external-debugger fork.
- Running binary: `~/duckstation/build-release/bin/duckstation-qt`, SHA-256
  `08a4720d1afc40f31f6961d3bd21625b17a49463a9c3d18336144e0acc856eab`.
- Movie: `g3native_movie.movie.json`, format v3, from boot, 6296 frames,
  SHA-256 `a311e6247537e206cd9056e18c915d6c3f08145ed189e118aac8b49ae3f81bbf`.
- Every runtime run used a recreated isolated config/port; no operator instance
  or normal DuckStation profile was used. Owned instances were stopped afterward.

## P61 causal correction

The native visual floor's absolute runtime anchor is:

`visual_anchor_rt = base_y_model(spawn) * runtime_scale`

For LEVEL01, `base_y_model(spawn) = -497` and `runtime_scale = 32`, so the
drawn GTE world is anchored at `-15904`. The old builder default anchored
collision and the spawn hook at `2144`, leaving a deterministic `+18048` runtime
unit separation. Stall-state cameras could see the displaced shell; normal
walking Y-band-culled it or exposed fill bands, producing the reported
"terrain when jumping / no terrain under Flik" behavior.

`tools/build_g3_native.py` now auto-aligns collision and runtime spawn to the
derived visual anchor for every surface JSON build. The old mismatch remains
available only through the explicit `--allow-misaligned-pa-rt` differential flag.

Regression evidence:

- `tools/regress_g3_native_authoring.py` asserts requested `2144` becomes
  effective `-15904`, collision samples use the effective anchor, and the
  explicit differential opt-in still preserves `2144`.
- Rebuild requested `--pa-rt 2144` and logged
  `auto-aligned collision/spawn anchor 2144 -> -15904`.
- `build/ABL_g3native_p61_auto.bin` SHA-256
  `b03d8eea0e6ead5a99c4cd95462393cc61a109d9a4724e51be5e98c0e83ea5c9`.
- Runtime patch report SHA-256
  `ba1dcd1d44b57d9012cc078ef0ca0531654afb48632219f710531ce06a1352ab`.
- Cold boot observed exact spawn `(197088,-12704,492896)`: floor `-15904`
  plus the normal body offset `3200`.
- `FUNC_80010000` executed 2189 times; Track-A `RENDER_C` executed zero times.
- Captures through frame 6170 show the authored pebbled floor under Flik during
  real movie-driven walking, not the disallowed post-movie stall state.

This confirms the global visual/collision anchor mismatch is fixed.

## Separate remaining collision frontier

The same long movie later falls inside the large P53 heightfield. A bounded route
trace localizes the first miss:

- last mapped swept response: frame 6207, authored replacement sector 175;
- at frames 6210..6220 feet-vs-authored-surface residual stays about
  `+218..+437` runtime units;
- by frame 6230 no swept response occurs and residual grows to `+1715`, then
  gravity carries Flik through;
- offline geometry still finds 9–11 authored planes under those X/Z points;
- coverage audit remains `not_a_clean_authored_collision_world`: 85 authored
  blocks on pristine-flat sectors, 86 replaced authored blocks, 11 malformed
  old-collision sectors (`178..188`), and 7 untouched outside blocks.

This is not the old 18048-unit global mismatch. It is the known P53 native
candidate/one-way swept-plane coverage frontier. The route trace is
`build/g3_native_p61_auto_route_trace.json` (SHA-256
`7e82f62f3c781ea6f07744b66935b7df5dbab017a0d67d8c9f401b86f0176ae7`).

Two globally aligned collision-lattice probes were rejected:

- expanding sector bounds to whole 1500-unit lattice cells stalled around movie
  frame 4730 (`ABL_g3native_p62_aligned`);
- preserving outer bounds and aligning only interior grid lines plunged around
  frame 5290 (`ABL_g3native_p62b_clipped`).

Neither probe is retained as a ship option. Do not retry global lattice alignment
without first tracing the selector footprint/grid-builder interaction.

## Conclusion

- **Confirmed:** GTE visual and authored collision/spawn must share the native
  `file_y * 32` absolute anchor. Builder enforcement is landed and regression-tested.
- **Historical audit result:** the `f51cbf...` ALLMODS image inspected at the start
  of this experiment did not include G3. The current composition result is recorded
  below and supersedes that image state.
- **Open:** broad free-roam collision still has a selector/swept-response miss.
- **Resolved:** composition uses the LEVEL01 overlay plus ISO reflow; it does not
  copy the standalone EXE over ALLMODS.

## ALLMODS composition follow-up

`tools/g3_bigland_stager.py` now layers Bigland through `mod/build.py` and moves
the P11 body/flags out of occupied resident ALLMODS space. `LEVEL01/LEVEL.BIN`
owns the P11 body at `0x800B4030`, flags at `0x800B4400`, and an init installer
at `0x800B44C0`. The installer copies two small three-marker gates to qualified
resident gaps and patches the player hook in RAM only once LEVEL01 is loading.

A disk-baked version of that gate was rejected. Differential smoke builds proved:

- ordinary ALLMODS control: BOOT/ALIVE/RENDER/WALK pass;
- control + disk-baked gate only: BOOT fails, player remains zero, black frame;
- overlay-init installed gate: all smoke checks pass.

The gate-only coverage recorded zero gate/overlay executions before failure. The
fault was front-end/movie timing perturbation from changing the global player-call
site on disc, not an executed Bigland collision path. Delaying the patch until the
LEVEL01 overlay init preserves the front end and still installs P11 before gameplay.

Final P63 composition:

- `build/ABL_ALLMODS.bin` SHA-256
  `cbce3f43f7f2cd9b7eea0a84e69c0add1575b6fb40531b2e0c18f93368658118`;
- runtime report SHA-256
  `dd0a9c8bf46fe67c368dc5c9ee54d9309dae42519cd8a765bca023901352ef5a`;
- embedded `LEVEL01/LEVEL.BIN` 2988 bytes, verified after ISO build;
- smoke: exact Bigland X `197088`, BOOT/ALIVE/RENDER/WALK pass, movement
  `139734`, sampled Y `-12923..-12732`.

## P63 visual-material correction

The operator correctly rejected P61's regenerated visual as square patchwork.
The cause was MOD-side and explicit in `build_grid_payload_styled`: every quad
independently position-hashed into the full harvested style pool. That mixed
different UV cells, rotations, batch controls, grass windows, and vertex tints
at quad frequency. Collision could match the surface while the material still
looked like a quilt.

P63 keeps the native GTE emitter/topology/density but makes the material coherent:
canonical pebble UV on every quad, neutral modulation, an explicit `0x0060` page
primer, and `0x8064` bit-15 detail controls. P61 contained 31 styles and 336 colors;
P63 contains two styles and two colors (pebble plus the deliberate marker tint).
The final smoke-frame SHA-256 is
`7c855375d152e7430b1e59b1981e27d9df5a2fcb208537ea9edb1df2ef00be6a`.

## Fixture correction / current collision blocker

The standalone `g3native_movie.movie.json` is desynchronized on ALLMODS and
selects Training/LEVEL00. Its GTE hits on the composed disc are therefore native
Training-floor hits, not Bigland evidence. Attempts to splice its gameplay tail
were also rejected because they began before the 4253-frame ALLMODS fixture had
finished loading LEVEL01. All owned instances were stopped; no such result is
used above.

`flik_to_level01_stall.mv.movie.json` is valid for the ALLMODS smoke gate, which
continues neutral frames until the player appears. A fresh ALLMODS→Bigland route
movie is now required to revisit the frame-6207 selector/swept-response frontier.

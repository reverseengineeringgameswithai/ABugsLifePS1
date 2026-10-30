---
kind: playbook
id: PLAYBOOK_mod_regression_troubleshooting
name: Mod regression troubleshooting — the post-campaign advantage
status: current
created: 2026-07-10
related:
  - EXP_2026-07-10_mod_smoke_gate
  - SYS_decomp_substrate
---

# Mod Regression Troubleshooting Playbook

**Why this note exists:** as of 2026-07-10 (dc campaign close + pivot to modding) the
project's regression story changed qualitatively. Historically, regressions cost
multi-session black-box debugging (the Tier-3 P18–P50 fault chain = ~30 probes for ONE
bug; the coldboot hang; the blackberry/grain-HUD cave collision). Every step of that
loop now has a purpose-built tool. Diagnosis should be **same-session, not
multi-session**. Work the ladder top-down:

## The troubleshooting ladder

1. **Catch it automatically — `mod/smoke_test.py --disc <X>.cue`** after *every* disc
   build ([[EXP_2026-07-10_mod_smoke_gate]]). BOOT / ALIVE / RENDER / WALK in ~5 min;
   PNG + JSON artifacts. A FAIL means a real boot/load/render/physics regression.
2. **Is it my change or the build? — the byte-exact baseline.** The substrate rebuild
   is SHA-1-provable (`af43de22…`, [[SYS_decomp_substrate]]), so a mod is a *diff
   against a known-good image*. `tools/validate_build.py` + the mod/build.py cave gate
   (memory map, FORBIDDEN_CODE_RANGES) answer "did I corrupt something structural"
   mechanically — entire regression classes (cave collisions, code-range clobbers)
   are now build-time errors, not runtime mysteries.
3. **Localize at runtime — the DuckStation debugger API** (isolated instance, never
   the operator's). Reach for the purpose-built call, not RAM brute force:
   write-watch (`accessLog`) = "who wrote this?"; `execTrace` = "what ran?";
   in-memory frame snapshot + `gpu.diffCurrentFrame` = "did the picture change, and
   where?"; `transferLog` = "where did this data come from on disc?";
   `experiment.run` = load → perturb → advance → diff.
4. **Understand the code at the fault address — it is no longer a black box.** Every
   resident function is classified and has a Canon `FUNC_<addr>` note; 287 are already
   readable C in `src/main/`. For the rest, **`tools/dc_m2c_seed.py --save <addr>`
   generates a structure/address/width-correct readable C seed on demand, in
   minutes** — decompile *reactively at the regression site*, never speculatively.
5. **Check the prepaid gotchas before deep-diving.** Most historical "regressions"
   were known interaction traps, now codified: R3000 load-delay in caves; LEVEL.RAW
   recompression size shifts / LBA reflow; save states masking disc edits (cold-boot
   the edited disc via movie replay instead); chunk-35 structural edits wedging the
   loader; heavy pokes destabilizing the instance (relaunch + fresh movie).

## Honest limits

- **Data-format interaction faults remain the top regression source** (LEVEL.RAW /
  LBA / structural chunk edits). They are guarded by convention (size-preserving
  tools, separate output discs) rather than proofs — the gate catches the *wedge*
  early; localizing the fault is still real (but documented) work.
- The smoke gate exercises **boot→LEVEL01 only**. ~30 recorded movies exist in the
  repo (training, bosses, seed levels); extend the gate with the relevant movie the
  first time a regression escapes it, not before.
- Emergent gameplay-logic bugs (value changed, behavior subtly wrong) still need
  human eyes — the ladder shortens diagnosis, it does not replace judgment.

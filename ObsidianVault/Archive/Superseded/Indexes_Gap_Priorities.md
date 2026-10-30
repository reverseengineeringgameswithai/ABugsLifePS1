---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Indexes/Gap Priorities.md
aliases:
  - "Gap Priorities"
migration_action: merge
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Indexes/Gap Priorities.md`
- Replacement/current location: `ObsidianVault/Canon/Indexes/Gap_Priorities.md`
- Archive reason: Index material should be regenerated around Canon IDs.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gap Priorities
type: index
updated: 2026-06-21
tags: [index, dashboard, gap-audit, roadmap, priorities]
---

# Gap Priorities — open backlog by priority

> Priority-grouped view of the **open** gaps. **Source of truth = [[Gap Audit]]** (full per-gap evidence + acceptance) and [[Roadmap]] §2. This note mirrors the Gap Audit index **as of 2026-06-22** and must be updated in the same pass when any status changes (the [[CONTRIBUTING]] M8 rule). The ~14 fully-resolved gaps (0007/0008/0009/0010/0011/0012/0014/0015/0018/0019/0022/0024/0041/0042) are omitted here — see [[Gap Audit]] for the full 43.

**Open counts:** P0 **0** · P1 **1** · P2 **0** · P3 **0** · closed-with-a-named-residual **26**. (1+0+0 open + 26 residual + 16 resolved = 43.) — **P3 closeout pass 2026-06-22: all 9 P3 gaps closed.** GAP-0006/0013 fully resolved (stale status); GAP-0027/0030/0031/0032/0035/0036 closed-with-residual; **GAP-0026 closed** — the round-trip exporter `tools/parse_all_anm.py` validates `.ALL` 78/78 + `.ANM` 58/58 byte-exact (acceptance met). The only open gap left is **GAP-0021** (P1, deferred decomp substrate).

## P0 — reproducibility (0 open)
Both P0 reproducibility gaps are **✅ Resolved on host (2026-06-21)** — see *Closed with a named residual* below. **No fully-open P0 remains.**
- **[[Gap Audit|GAP-0002]]** — Critical inputs untracked; findings-store overwrite hazard — **was** the top open P0; **closed on host 2026-06-21** (commit `fb7b9a0`): a load-before-save guard + fixture hash-pinning now exist. Moved to the residual group.

## P1 (1)
- **[[Gap Audit|GAP-0021]]** — No decompilation build/diff substrate (C un-compilable / un-diffable) — *Deferred — payoff-gated* (charter; reaffirmed 2026-06-21 — no concrete modding payoff requires it; enabling symbols/overlays are the active part).

## P2 (0)
GAP-0034 (the lone P2) is now **✅ Behavior decoded (2026-06-22)** — moved to *Closed with a named residual* below. **No fully-open P2 remains.**

## P3 (0)
All P3 gaps are closed (2026-06-22). GAP-0026 (the last open one) is now resolved — see *Closed with a named residual* below. **No open P3 remains.**

## Closed with a named residual (honest picture — not 100% done)
### P3 closeout pass (2026-06-22)
- **[[Gap Audit|GAP-0026]]** — `.ALL`/`.ANM` fine-grammar — **✅ Resolved**: committed round-trip exporter **`tools/parse_all_anm.py`** validates **`.ALL` 78/78 + `.ANM` 58/58** byte-exact (`emit(parse(x))==x` = the proof). The decode **corrected 3 prior claims** (no `.ANM` per-frame bitmask = dense frame-major; ACORN/BBIRD/FDIM = just `anim_count==2`, not "compact-inline"; on-disk prim type = the *last colour word's* `cmd & 0x3c`, not a leading type word). `.ANM` fully field-typed; `.ALL` primitive layer field-typed (6634 records), skin-attachment tails + section-B mini-headers byte-preserved. Residual = semantic field-typing of those `.ALL` spans (reproduction already exact).
- **[[Gap Audit|GAP-0006]]** — Build artifacts in `tools/` — **✅ Resolved**: the gap status was **stale**; tracked `tools/` already holds only source + the **2 hash-pinned codec oracles** (`raw_chunk0_{compressed,decompressed}.bin`, allowlisted in `verify_repro_inputs.py` + `test_no_forbidden_artifacts.py`); generated artifacts are gitignored (`tools/*.png`, `tools/LEVEL_*.RAW`, `*.decompressed`). Residual = untracked `_step3.py` scratch (never committed).
- **[[Gap Audit|GAP-0013]]** — Level-editor README tab disclaimer — **✅ Resolved**: status was **stale**; `level_editor/README.md` (line 57) already distinguishes legacy "3D Tools" (mutation not wired *there*) vs the working "3D Scene" tab (drag-to-move → `Operation.move`). Acceptance MET.
- **[[Gap Audit|GAP-0027]]** — GFX CLUT exactness — **✅ Resolved (static + live)**: the floor CLUT is embedded in **`LEVEL01/LEVEL.RAW`** (not GFX/, refuting the "uploaded separately" premise); live VRAM CLUT (`gpu.readVramRect 960,255`) reproduced **14/16 exact** by `(R>>3)|(G>>3)<<5|(B>>3)<<10 \| 0x8000`. Residual = 2-LSB rounding on 2/16 + a `decode_gfx.py` generalization.
- **[[Gap Audit|GAP-0030]]** — OT / GPU-packet + frame-flip — **✅ Resolved (static + live)**: OT = **DMA linked-list in the active framebuffer** (`gp0Trace`: `source:dma`, E1/E3/E4/E5 + prims); flip = `0x80062CFC`→**`0x800646B8`** (VSync-wait + DrawOTag-DMA); buffer toggle `0x801E124C`↔`0x801CC390` live-confirmed. Residual = per-frame OT node count/sort depth.
- **[[Gap Audit|GAP-0031]]** — Runtime audio (SPU) — **✅ Resolved (static, documented path)**: SFX `0x80050994` dispatcher (← pickup `0x80054288`) + libspu `SsVabOpenHead 0x8006b130`/`SsVabTransBody 0x8006b1c0` via VAB loader `fcn.80042fa0`; music = XA `CdlReadS`/`CdlSetfilter` + per-level table `0x8001b0e0`. Residual = a *positive* live SFX-event trace + voice key-on + XA channel map (idle-Flik probe = 0 hits).
- **[[Gap Audit|GAP-0032]]** — In-engine FMV trigger — **✅ Resolved (static)**: `FMV.BIN` = a **25-entry manifest** (= the front-end sequence: TT→DLOGO→AD→LEV1A/1B…LEV9B) loaded by `0x8003e7c0`→`0x80046330` to Region-B `0x800B5788`. Corrects a bogus "MDEC=0x80010000" guess. Residual = the MDEC decode call site (overlay-resident, `0x800B5788+`).
- **[[Gap Audit|GAP-0035]]** — Live level-warp — **Split / terminal reframe ADOPTED**: 0035A spawn/landing/transition **architecture Verified**; 0035B clean in-game level→level handoff is **terminal-by-design** (the destination index `0x8008245c` is shell-only-writable; the type-6 gameplay exit force-sets the invalid scene 16) — not a bug to lever around. The shell-phase event-state fixture is the only path (GAP-0033-gated).
- **[[Gap Audit|GAP-0036]]** — Menu / save state machine — **✅ Resolved (static overlay disasm)**: menu-nav + memory-card code are in the **`MEMORY.BIN` overlay** (`0x800B5788`), not the EXE — cursor handler `0x800B687C`, save writer `0x800BAF30` (open mode=2 → `0x200`+`0x380` write), `SC`-magic 8 KB block (`0x800BAD08`), filename `BASCUS-94288`. Residual = live save write-watch + the `0x380` body field map.

- **[[Gap Audit|GAP-0023]]** — Chunk-34 mesh + model→world — **✅ Resolved for the floor (2026-06-22)**: offline **`world = T_obj + v_local`** read from the LEVEL.DAT node array (LEVEL01 @`0x45f0`, stride `0x18`; `T_obj`@+0/4/8, payload@+0x14); 3-way disk==runtime==formula + cross-level static (L04/L05); chunk-34 = not-drawn (B7); visible terrain = `FUNC_80010000`. Editor fix **APPLIED + tested** (2026-06-22, untracked `level_editor/`: `survey_node_anchors` from the 0x18-stride node array @0x45f0 + `scene3d` `world=T_obj+v`; tests 16/16+9/9+6/6; `diag_spawn` pickups-with-no-floor **10/70→0/70**; under-Flik tile @ world (6113,71,15525)). Residual = rotated-mesh `M_obj`, decor Y-flip, cross-level *live* provenance, `floor_terrain` class heuristic.
- **[[Gap Audit|GAP-0004]]** — Legal/preservation-sharing policy note — **✅ Resolved (2026-06-22)**: [[Preservation Policy]] exists + linked from Index/README/Home + `.gitignore` names it (the prior "write the note" was stale; no real residual).
- **[[Gap Audit|GAP-0017]]** — No CI / test runner — **✅ Resolved (2026-06-22)**: `.github/workflows/safe-tests.yml` committed + `run_safe_tests` 40 passed locally; gpu/live/local_media isolated. Residual = observed green run on GitHub (operator push; no remote yet).
- **[[Gap Audit|GAP-0040]]** — Codec/live regression — **✅ Resolved (2026-06-22)**: codec round-trip CI-green + opt-in `live` skip-guarded replay (`tests/test_live_replays.py` → `trace_spawn_floor.py`, `ABL_LIVE` gate). Residual = re-run the other 3 replays from preserved state + off-host (operator).
- **[[Gap Audit|GAP-0016]]** — PsyQ/toolchain census — **✅ Resolved (2026-06-22)**: census + tool pins; PsyQ libs **dated ≥1997-03-28** via EXE RCS `$Id$` (sys.c/intr.c/bios.c). Residual = exact `ccpsx` compiler revision = GAP-0021-gated (deferred).
- **[[Gap Audit|GAP-0028]]** — Camera follow-law — **✅ Resolved (follow-law, 2026-06-22)**: `fcn.8004df18` boom/orbit-behind-player + per-axis smoothing `C+=(target−C)>>3` (k=1/8); behind `dist=900`×32, `HEIGHT=12288`; reads player `0x800a6500` + sin table `0x80074970`; struct `0x80095358` → scratchpad `0x1f800374`. Validated (0 error phase-aligned; ≤3.6 editor units). Residual = closed-form heading/pitch + collision boom-pull-in + RT→GTE projection (byte-exact pixels) + non-normal modes.
- **[[Gap Audit|GAP-0005]]** — Asset extractors — **✅ Resolved (2026-06-22)**: committed `tools/extract_vab.py` (PS1 VAB→WAV, **1771/1771 byte-match** vs known-good) + `extracted/SHA256SUMS` (1879 entries, `sha256sum -c` clean; tracked via `.gitignore` negation, hashes only). GFX/BGR via tracked `decode_level_raw.py`. Residual = XA/FMV regen via external pinned **jpsxdec v2.1-beta** (documented recipe, by design).
- **[[Gap Audit|GAP-0020]]** — Overlays Region A/B — **✅ Resolved (2026-06-22)**: M3 baseline meets the acceptance (regions enumerated + **multiple** overlays behavior-mapped: `0x800b39a4`/`0x800b3aec`/`0x800b3bb8` + spawn census + Region-B loader). Residual (deferred-by-design) = full LEVEL1.BIN/Region-B enumeration + live scene→variant residency.
- **[[Gap Audit|GAP-0029]]** — CD streaming/caching — **✅ Resolved (2026-06-22)**: model documented (loader chain `FUNC_80046330`/`8003CF2C`/`8003A318` + by-name) + **level geometry = all-at-load** (TERRAIN.ALL cache refuted, 0 EXEC hits); FMV/XA streamed. Residual = does ANY mid-level streaming exist (event-gated, GAP-0033) + PATH*.BIN runtime role.
- **[[Gap Audit|GAP-0025]]** — Size-changing/LBA-shift disc edits — **✅ Resolved (2026-06-22)**: built an oversize reflow (grow `MEMORY.BIN` +8192 B → **274/276 files shift +4 sectors**) + **booted it → LEVEL01 loaded in-level** (Flik at spawn point, collision populated) ⇒ in-level loading is **by-name / LBA-shift-tolerant**. Unblocks oversize content mods. Residual = optional committed reflow builder (`tools/build_reflow_image.py`).
- **[[Gap Audit|GAP-0039]]** — RE depth generality — **✅ Resolved (2026-06-22)**: a non-LEVEL01 level (LEVEL02 = on-disc LEVEL03) now has a **deep chunk+collision map** — floor render-source per-pixel (M7) + collision table `0x800a7e48` (602 sectors) source-correlated to disc chunk 28→29 (byte-identical modulo 4 reloc slots) + **motion-validated** (walk: candidate planes track Flik, footing grounded, resolver fires every frame). Floor format confirmed across all 10 gameplay levels (11/11 explained); sub-types decoded (0x08/0x09 = render-param shading variant @`0x800a3390`; 0x04 = steeper non-floor; primitive format is per-command). Residual = collision beyond LEVEL02 + optional live counterfactual.
- **[[Gap Audit|GAP-0003]]** — Host-hardcoded paths + no dependency manifest in `tools/` — **✅ Resolved (2026-06-21)**: **0** `/home`/`/Users` literals in any tracked `tools/*.py` (enforced by `tests/test_path_portability.py`, now scanning `tools/`+`tests/`), host locations via `tools/_env.py`, pinned `tools/requirements.txt` + `pyproject.toml` (`run_safe_tests.py` → 40 passed); residual = untracked WIP tools import `numpy`/`PIL` (declare when promoted to tracked) + docs still cite `~` as the operator host path (descriptive).
- **[[Gap Audit|GAP-0043]]** — Charter recorded; legacy preservation scorecard not reconciled — **✅ Resolved (2026-06-21)**: [[Blockers]] scorecard + severities relabeled an *optional* harder-yardstick gauge (charter-linked banner + "Gauge, not goal" note), B1's "won't-do" callout → **deferred/payoff-gated** (enabling symbols/overlays active), [[Risk Matrix]] already reconciled; residual = cosmetic charter-links on a few individual B-notes + operator-WIP [[Project Index]].
- **[[Gap Audit|GAP-0001]]** — Dynamic evidence rode one private emulator fork — **✅ Resolved on host**; residual = copy the verified preservation set **off-host** (operator-only; `origin` is upstream stenzek).
- **[[Gap Audit|GAP-0002]]** — Critical inputs untracked; findings-store overwrite hazard — **✅ Resolved on host (2026-06-21)** (commit `fb7b9a0`: two-layer findings guard `tools/check_findings_store.py` + hash-pinned fixtures `tools/fixtures.sha256` + no-forbidden-artifact test); residual → **[[Gap Audit|GAP-0040]]** (scripted from-boot fixture regeneration; reconcile `SCUS-94288_3.sav` vs `level02.sav`).
- **[[Gap Audit|GAP-0033]]** — Scripting / event-trigger system — **Verified** (mover/object-actor bytecode VM [[FUNC_8004C13C]] fully modeled — 26 opcodes decoded/bounded, cold-boot stream captured); narrow runtime residuals.
- **[[Gap Audit|GAP-0034]]** — AI/enemy behavior — **✅ Behavior decoded, cross-level (2026-06-22)** → [[Enemy AI state machine]]: regular enemies across scenes 1/3/4/5/6/10 = two shared routines (chaser `FUNC_8004DF18` @`0x80095358` Flik-homing + EVENT-gated strike; mover-VM [[FUNC_8004C13C]] patrol/anchor), NO new AI fns; **BIRD boss bespoke** (`FUNC_8004DD98`) decoded; **HOPPER + THUMPER both fight as the chaser AI** (`FUNC_8004DF18` @`0x80095358`, multi-phase via `0x80082488`) — **Thumper PARTIAL** — actor + Y-law (target-Y=Flik.Y−512) + defeat-chain (`0x80090bee`bit0→`FUNC_8004DA94`→bird) decoded from the COMPLETE `thumper_boss_2.movie`, but **HP / mosquito-throw / berry are in the boss COMBAT OVERLAY `0x800b4xxx`/`0x8009c0xx` (OPEN** — resume `transferLog.resolve 0x800b4138`); the bespoke `FUNC_8004DD98` @`0x80090bc0` = scripted finale (bird + Thumper end-approach + Hopper bird-defeat). **THUD untested.** Live over 5 LEVEL01 + 9 cross-level + 5 boss-movie fixtures. **Dragonfly aggro-gate RESOLVED 2026-06-22** = chasers pursue only a *moving* Flik (gate `[0x800a6538]≠0` @`0x8004e0a0`; shared chaser gate). Residuals = Thumper combat-overlay (HP/throw/berry; resume `transferLog.resolve 0x800b4138`) · Hopper defeat · Thud re-test · Flik HP-counter field · `PATH*.BIN` decider.
- **[[Gap Audit|GAP-0037]]** — Player input→movement law — **Decoded / acceptance MET** (M6, static + runtime-confirmed) but tagged **local-only** (not the formal ✅ keyword) per GAP-0001 discipline.
- **[[Gap Audit|GAP-0038]]** — Headline results single-source — **Verified** (G29 Pass-3 counterfactual, both arms; visual≠collision meets the ≥2-method bar); optional 2nd-edit / non-LEVEL01-scene hardening left.

## Practical read
After the **2026-06-22 P3 closeout pass — all 9 P3 gaps closed** — the only open gap is **GAP-0021** (P1, deferred/payoff-gated decomp substrate). Everything else is Resolved or closed-with-a-named-residual. The P3 subsystem gaps (rendering OT/flip, SPU audio, FMV, menu/save) were closed via the live debugger (GAP-0001 harness) + static EXE/overlay disasm — each carries a small named residual (a positive live audio trigger, the MDEC overlay decode site, a live save write-watch, OT node-count). The highest-value remaining *reproducibility* step is still the **GAP-0001 off-host copy** (operator-only).

## See also
[[Gap Audit]] · [[Roadmap]] · [[Open Questions]] · [[Reproducibility Checklist]] · [[Fixtures Index]] · [[Project Index]]

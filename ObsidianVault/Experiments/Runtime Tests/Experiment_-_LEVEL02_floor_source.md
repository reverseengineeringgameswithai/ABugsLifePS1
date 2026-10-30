---
kind: experiment
id: Experiment_-_LEVEL02_floor_source
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - LEVEL02 floor source.md
aliases:
  - "Experiment - LEVEL02 floor source"
  - "Verification - M7 Headline Recheck"
---

# Experiment — LEVEL02 floor source (GAP-0039)

> Migrated from `ObsidianVault/Experiments/Experiment - LEVEL02 floor source.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — LEVEL02 floor source (GAP-0039)

> **M7 cross-level confirmation.** Takes the LEVEL01 headline ([[Experiment - Spawn-floor render source]] — visible floor under Flik = LEVEL.DAT via `fcn.80010000`, distinct from the chunk-32 collision sector table) and proves it **per-pixel on a second stage, LEVEL02 (scene_id 3)**. It also **corrects** the first LEVEL02 pass ([[Verification - M7 Headline Recheck]]), which reported `fcn.800172dc = 0 calls` — a single-frame sampling artifact. Replayable via `tools/trace_level02_floor.py`.

## Question
At Flik's position on **LEVEL02**, which renderer draws the visible floor pixel under him — the LEVEL.DAT driver `fcn.80010000` (as on LEVEL01) or the chunk-35/`.ALL` driver `fcn.800172dc`? And is the visible source still distinct from the collision sector table `0x800a7e48`?

## Fixture / environment
- **Disc:** `Disney-Pixar A Bug's Life (v1.0).cue` — **pristine**, cue SHA-256 `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644` (same pristine image as [[Experiment - G29 Pass-3 differential]] Arm A), serial `SCUS-94288`.
- **Save state:** `~/Downloads/ABL/level02.sav` — SHA-256 `9c4cd968151e8c2f630b89b58a9da90e9143de6bd5b14c859e2b783d12f7f152`, `emulator.getStateInfo` `media_path` == the pristine cue (checked before load; gitignored fixture).
- **Instance:** isolated DuckStation fork, port 23460, token `debugger-1000`, config `/tmp/duckstation-debugger`; fork HEAD `296955321`, binary SHA-256 `796965d722…6501` (50 dirty entries). Local-only → **GAP-0001**. Instance stopped + confirmed down after capture.
- **At rest:** `scene_id [0x80082504] = 3` (LEVEL02); Flik world XYZ = **(-16896, 32043, 6631)**; this stage's `G_DAT_BASE_PTR [0x80082498] = 0x8015e22c` (different base from LEVEL01 — classification is **base-relative**).

## Method + exact calls
Driver: `python3 tools/trace_level02_floor.py --save ~/Downloads/ABL/level02.sav --output /tmp/level02-floor.json` (host-portable; `--port/--token/--disc/--frames/--picks` overridable). Hardened like the G29 replays (getStateInfo media match, `validate_disc:true`, `auto_select_disc:false`, settle-then-pause).
1. **Identity guard (anti-swap):** disasm `fcn.80010000` and `fcn.800172dc` entries to confirm two distinct functions (the project has a known `0x80010000↔0x800172dc` confound).
2. `gpu.pickObject {x,y}` on eight lower-centre pixels (native CRTC 512×224) → the floor packets under Flik.
3. `accessLog.addWatch {address:<floor packet>, length:16, type:"write"}` → `advanceFrames 3` → `accessLog.get` for each distinct GP0(3c) packet → the writer PCs.
4. **Decisive caller attribution:** `execTrace.addWatch {pc:<floor-leaf store PC>, capture:["pc","ra"]}` over a multi-frame window → the `ra` (driver) that called the shared leaf.
5. `execTrace.addWatch {pc:0x80010000, capture:["pc","a0"]}` over 4 frames → robust `a0` source-region classification.
6. `execTrace.addWatch {pc:0x800172dc, capture:["pc"]}` over 4 frames → call count.
7. `debugger.readMemory 0x800a7e48` → collision sector table populated + separate.

## Addresses / functions
| Symbol | Address | Role |
|---|---|---|
| current_scene_id | `0x80082504` | 3 == LEVEL02 |
| G_DAT_BASE_PTR | `0x80082498` → `0x8015e22c` | LEVEL02 runtime LEVEL.DAT base |
| DAT mesh driver | [[FUNC_80010000]] | calls the shared leaf to emit the floor |
| shared GTE leaf emitter | `0x80019xxx` (store `0x8001993c`…) | `mfc2 sz1/2/3`, builds GP0(3c) quad, OT-links via `lui 0x0c00` |
| leaf call sites in `fcn.80010000` | `0x8001067c`, `0x800108b8` | the `ra` values proving DAT-driver ownership |
| chunk-35/.ALL driver | [[FUNC_800172DC]] | active, but draws other meshes (not the floor) |
| collision sector table | `0x800a7e48` | LEVEL.RAW chunk 32 (footing) |

## Observed (2026-06-21)
- **Function identity:** `fcn.80010000` = `addi sp,sp,-32; lw t7,0(a0); sw s7,0x1c(sp)` (real prologue, reads `a0`); `fcn.800172dc` = `lui v0,0x1f80; …; lhu t0,0(a1)` (reads `a1`). Two distinct functions — no swap.
- **Floor pixels** = `GP0(3c)` textured quads, texpage `x=64,y=0`, packets `0x801d0d68 / 0x801d0f3c / 0x801d0af8`.
- **Floor packet writer** = the **shared GTE leaf** at `0x80019xxx` (`0x8001993c/978/a00/a78` for `0x801d0d68`). On LEVEL01-spawn the *same* driver emitted **inline** (`0x800107b0..0x800108a8`); here it **calls out** to the leaf — same driver, different emit site.
- **Decisive caller attribution:** the floor-leaf store `0x8001993c` is hit **40×** over the window and **40/40 `ra` are inside `fcn.80010000`**; distinct callers = **`0x8001067c` and `0x800108b8`** (both inside `fcn.80010000`, next to the LEVEL01 inline-writer PCs). ⇒ the LEVEL02 floor leaf is driven by **`fcn.80010000` (the DAT path)**.
- **Source region (robust, 4 frames):** `fcn.80010000` runs **16×** with **16/16 `a0` in DAT** (span `0x80165430..0x8018e2c4` = DAT file `0x7204..0x30098`, above `G_DAT_BASE 0x8015e22c`). **0** chunk-35 reads.
- **`fcn.800172dc` = 16 calls/4f** — **active**, but it draws *other* geometry; its store does not feed the picked floor packets (the `ra` attribution is exclusively `fcn.80010000`).
- **Collision** sector table `0x800a7e48[0] = 0x16060` populated (head-512 SHA-256 `01327664f907f4d6…`), in a separate RAM region (below the DAT base).

## Correction of the first LEVEL02 pass
The first pass ([[Verification - M7 Headline Recheck]]) reported `fcn.800172dc = 0 calls`. A **single-frame** `execTrace` window races the frame boundary: an isolated one-frame snapshot here flipped between `fcn.80010000 = 0` and `fcn.800172dc = 0`. The **robust multi-frame** measurement shows **both** drivers active (~4 calls/frame each); the floor *specifically* is `fcn.80010000`/DAT (proven by the `ra` attribution), while `fcn.800172dc` draws other meshes. The corrected model: *both renderers run; the visible floor under Flik is the DAT driver*. The tool now uses multi-frame windows for every count and capture.

## Conclusion
**On LEVEL02 (scene 3), the visible floor pixel under Flik is LEVEL.DAT-backed, emitted by `fcn.80010000` (via the shared GTE leaf `0x80019xxx`, called from `0x8001067c/0x800108b8`), reading DAT payloads at `0x8016xxxx..0x8018xxxx`. Collision is the separate chunk-32 sector table `0x800a7e48`.** This **generalizes the LEVEL01 visible-floor-source headline to a second stage at the per-pixel level** (not just the aggregate source classification of the first pass) and corroborates visual ≠ collision on LEVEL02.

## Evidence grade
- **Confidence: CONFIRMED** for the floor-source attribution **on this LEVEL02 fixture/position** — four corroborating dynamic methods (per-pixel pick → packet write-watch → writer leaf; leaf `ra` caller-attribution → `fcn.80010000`; `fcn.80010000` `a0` source = DAT 16/16; the negative that `fcn.800172dc` does not feed the floor packet) + the function-identity guard. Deterministic across re-runs (the replay self-checks and exits non-zero on any flip).
- **Bounded scope:** one stage, one Flik position; **no LEVEL02-specific counterfactual edit** (the visual≠collision *causality* still rests on the LEVEL01 G28/G29 counterfactual + architecture). Generality across **all** 12–15 stages remains **LIKELY**, now with one stage proven per-pixel.
- **Reproducible without the operator's environment:** **No** — isolated fork + pristine disc + `level02.sav` (gitignored) → **GAP-0001**. One-command replay on the operator's machine (GAP-0040).

## Gap status changes
- **GAP-0039 → advanced** (In Progress, stronger): the per-pixel floor pick→writer→caller attribution is now done on a non-LEVEL01 stage; upgrades the first-pass *aggregate* classification (LIKELY-strong) to a **CONFIRMED per-pixel** floor-source attribution on LEVEL02. Full per-stage maps + a LEVEL02 counterfactual remain.
- **GAP-0040 → advanced**: a 4th hardened headline replay (`tools/trace_level02_floor.py`) — identity/disc guards, deterministic JSON, self-checking verdict, no media.
- **GAP-0011/0038**: corroborated on a 2nd stage (visible floor = DAT; collision = separate chunk-32 table).

## Related
[[Experiment - Spawn-floor render source]] · [[Experiment - G29 Pass-3 differential]] · [[Finding - Visual is not collision]] · [[Finding - Candidate A is DAT-backed visual terrain]] · [[FUNC_80010000]] · [[FUNC_800172DC]] · [[API - gpu.pickObject]] · [[API - accessLog]] · [[API - execTrace]] · [[Verification - M7 Headline Recheck]] · [[Playbook - Replay headline experiments]] · `tools/trace_level02_floor.py`

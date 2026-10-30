---
kind: experiment
id: Experiment_-_Spawn-floor_render_source
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Spawn-floor render source.md
aliases:
  - "Experiment - Spawn-floor render source"
---

# Experiment — Spawn-floor render source (GAP-0011)

> Migrated from `ObsidianVault/Experiments/Experiment - Spawn-floor render source.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — Spawn-floor render source (GAP-0011)

> **M7 headline recheck.** Picks the LEVEL01 **spawn-area floor under Flik** on a **pristine** disc and traces its draw-call provenance, resolving the standing contradiction between *"visible floor = LEVEL.DAT"* and *"the spawn ground is LEVEL.RAW chunk 34/35."* Replayable via `tools/trace_spawn_floor.py`.

## Question
At Flik's **actual spawn position** in LEVEL01, which resource renders the visible floor he stands on — the **LEVEL.DAT** mesh payload (emitter [[FUNC_80010000|fcn.80010000]]) or the **LEVEL.RAW chunk 34/35** geometry (renderer [[FUNC_800172DC|fcn.800172dc]])? And is that visible source distinct from the **collision** floor (chunk-32 sector table `0x800a7e48`)?

## Prior claims being challenged
- [[Finding - Candidate A is DAT-backed visual terrain]] (G28): the visible walkable floor is a LEVEL.DAT payload drawn by `fcn.80010000` (CONFIRMED only for a localized patch, `g30_openground`).
- `Finding - Chunk 34 master mesh structure` (editor-track WIP, untracked): the **spawn ground is chunk 34/35**, and *"DAT terrain does not cover the spawn area (DAT terrain Z ≤ 9774 vs Flik at Z 15403)."* — directly contradicts the above for the spawn region.
- The findings store still holds two CONFIRMED visible-floor answers (f5/f10 vs f13; GAP-0008).

## Fixture / environment
- **Disc:** `Disney-Pixar A Bug's Life (v1.0).cue` — **pristine** (no edits), `game_serial == SCUS-94288` (asserted).
- **Save state:** `~/.local/share/duckstation/savestates/SCUS-94288_1.sav` — LEVEL01 at Flik's exact spawn (operator re-saved 2026-06-21). On the pristine image, so it reflects no disc edits.
- **Instance:** isolated DuckStation fork, port 23460, token `debugger-1000`, config `/tmp/duckstation-debugger` (never touches the operator's own DuckStation). Local-only → **GAP-0001**.
- **At rest:** `scene_id [0x80082504] = 1` (LEVEL01); Flik world XYZ = **(197091, 2734, 492897)** → file Z = 492897 >> 5 = **15403** (exactly the Z the chunk-34 note said DAT does not reach).

## Method + exact calls
Driver: `python3 tools/trace_spawn_floor.py` (host-portable; `--port/--token/--save` overridable). The decisive RPC sequence:
1. `emulator.loadState {path: SCUS-94288_1.sav, pause_after_load:true}` → `emulator.advanceFrames {frames:4}` → `debugger.pause` (settle for a coherent frame).
2. `gpu.pickObject {x,y}` on five brown-floor pixels (native CRTC 512×224): `(300,150) (340,135) (256,200) (210,160) (200,165)`.
3. `accessLog.addWatch {address:<floor packet>, length:16, type:"write"}` → `advanceFrames 3` → `accessLog.get` (who writes the packet).
4. `execTrace.addWatch {pc:0x80010000, capture:["pc","a0"]}` → `advanceFrames 1` → `execTrace.get` (classify the mesh-descriptor source region for **every** emitter call).
5. `execTrace.addWatch {pc:0x800172dc, ...}` → `advanceFrames 1` (does the chunk-35/.ALL renderer run at all?).
6. `debugger.readMemory 0x80082498` (G_DAT_BASE_PTR), `0x800a7e48` (collision sector table).

## Addresses / functions
| Symbol | Address | Role |
|---|---|---|
| current_scene_id | `0x80082504` | 1 == LEVEL01 |
| Flik world X/Y/Z | `0x800a6500/04/08` | spawn (197091,2734,492897) |
| G_DAT_BASE_PTR | `0x80082498` → `0x801607f8` | runtime LEVEL.DAT base |
| DAT mesh/poly emitter | [[FUNC_80010000]] (`0x800107b0/82c/838/8a8`) | writes the floor GP0(3c) quad packet |
| chunk-35 / .ALL renderer | [[FUNC_800172DC]] | the *other* candidate (occluded terrain + actors) |
| collision sector table | `0x800a7e48` | LEVEL.RAW **chunk 32** (footing) |
| floor packets (this state) | `0x801d2xxx–0x801d5xxx` | GP0(3c) quads, texpage `0x660` |

## Expected
If "visible floor = DAT" generalizes to the spawn area, the floor packet is written from inside `fcn.80010000` and its `a0` source pointers sit in the DAT region (`≥ 0x801607f8`). If the chunk-34 note is right, the floor is drawn by `fcn.800172dc` reading the chunk-35 buffer (`0x8012cxxx`).

## Observed (2026-06-21)
- **Floor pixels** = `GP0(3c)` textured **quads**, texpage `0x660`, brown (e.g. rgba [74,57,57]); packets clustered `0x801d2160–0x801d5674`. (Flik's body is a *separate* bluish object, packets `0x801cdxxx`, texpage `0x604/0x64a`.)
- **Packet writer** = PCs `0x800107b0 / 0x8001082c / 0x80010838 / 0x800108a8` — **all inside `fcn.80010000`**; header write value `0x3c605c5c` = the `GP0(3c)` quad command. (`accessLog.lastWriter` returns nothing post-`loadState` — the write ring is empty until a watch is armed; hence the write-watch.)
- **Source region** = **20/20** `fcn.80010000` calls in the frame read `a0` from the **DAT region**, span `0x801765e4..0x8018fd94` = **DAT file offsets 0x15dec..0x2f59c**. Candidate A's file offset `0x188cc` lies inside this span → the spawn floor is the **same DAT-payload family** G28 edited. **Zero** calls read the chunk-35 buffer.
- **`fcn.800172dc` = 0 calls** this frame — the chunk-35 / shared-`.ALL` renderer does **not** draw the spawn scene at all.
- **Collision** sector table `0x800a7e48` is populated (`[0]=0xf80`) in a **different RAM region** from the DAT visible mesh (`0x8018xxxx`).

## Conclusion / reconciliation
**The visible spawn-area floor under Flik (file Z 15403) is LEVEL.DAT-backed, emitted by `fcn.80010000` reading DAT payloads at ~`0x8018xxxx`. It is NOT chunk-34/35.** This **generalizes "visible floor = DAT" to the spawn area** and **refutes** the chunk-34 note's "DAT does not cover the spawn area" *for the visible render*. The reconciliation across the three work-streams:
- **Visible floor (incl. spawn)** = LEVEL.DAT, `fcn.80010000`. ← this experiment.
- **chunk-34/35** = the **occluded / non-visible** terrain layer (consistent with GAP-0009: "chunk-35 fires but ~0 visible px") and/or the collision-adjacent geometry — **not** the visible spawn renderer. The chunk-34 note's static "DAT terrain Z ≤ 9774" measured one payload bound; the runtime shows DAT meshes spanning file `0x15dec..0x2f59c` covering the whole spawn view.
- **Collision** = LEVEL.RAW **chunk 32** sector table `0x800a7e48`, a separate RAM region from the DAT visible mesh → **visual ≠ collision** holds at the spawn area by **source separation** (a second, independent angle on GAP-0038, distinct from the G28 edit).

## Evidence grade
- **Confidence: CONFIRMED** — three independent **dynamic** methods this session (pick→write-watch; per-call source classification; the `fcn.800172dc`=0 negative) + one **historical counterfactual** (G28 DAT edit visibly deformed terrain). Corroborated by **static** disassembly of `fcn.80010000` (a0 = mesh descriptor, scratchpad GTE poly emitter).
- **Static or dynamic:** both (dynamic-primary, static-corroborated).
- **Reproducible without the operator's environment:** **PARTIAL.** One-command replay (`tools/trace_spawn_floor.py`, tracked, ships no media) on the **operator's** machine; **not third-party-reproducible** until the fork + disc + `SCUS-94288_1.sav` fixture are preserved (**GAP-0001/0002**). The fixture is a local `.sav` (gitignored) — name + frame recorded here per the evidence rubric.

## Gap status changes
- **GAP-0011 → Verified** (was Needs Evidence): the spawn-floor source is named with pick+trace evidence (DAT / `fcn.80010000`); the chunk-34 contradiction is reconciled (visible ≠ occluded/collision).
- **GAP-0038 → advanced**: adds a second, independent confirmation of visual ≠ collision at the spawn area (source separation). The pristine-vs-patched **G29 Pass-3** differential is still owed → [[Experiment - G29 Pass-3 differential]].
- **GAP-0008 (findings store)**: the live evidence to make **f13 the single CONFIRMED** visible-floor answer and mark f5/f10 Superseded now exists (operator edit; load-before-save).
- **GAP-0009/0010**: corroborated — `fcn.800172dc`/chunk-35 is not the visible spawn renderer.

## Related
[[Finding - Candidate A is DAT-backed visual terrain]] · [[Finding - Visual is not collision]] · `Finding - Chunk 34 master mesh structure` (operator WIP — reconcile per above) · [[FUNC_80010000]] · [[FUNC_800172DC]] · [[API - gpu.pickObject]] · [[API - accessLog]] · [[API - execTrace]] · [[Experiment - G29 Pass-3 differential]] · [[Playbook - Replay headline experiments]] · [[Verification - M7 Headline Recheck]] · `tools/trace_spawn_floor.py`

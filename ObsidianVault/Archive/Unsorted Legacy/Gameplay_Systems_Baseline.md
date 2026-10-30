---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Gameplay Systems Baseline.md
aliases:
  - "Gameplay Systems Baseline"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Gameplay Systems Baseline.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gameplay Systems Baseline
type: core
updated: 2026-06-20
tags: [core, gameplay, milestone6, gap-0033, gap-0034, gap-0035, gap-0036, gap-0037]
---

# Gameplay Systems Baseline (M6 scoped start)

> Milestone 6 entry map — what's known/unknown across the five gameplay subsystems, the gap each maps to, modding relevance, and the **fixtures** that unblock them. This is a *scoped start*, not the whole milestone; the chosen first lane is **events/triggers** → [[Gameplay - Events and Triggers]] (GAP-0033, the keystone). **Provenance:** STATIC = reproducible from `SCUS_942.88` disasm + `symbols/re_symbols.sym`; **DYNAMIC = local-only** on the dirty fork ([[DuckStation Fork Reproducibility]] / GAP-0001).

> [!important] The binding constraint behind most of M6 is one missing fixture
> Every save state on hand is **mid-gameplay**. The event/callback path, gated LEVEL.DAT records, `PATH*.BIN`, the warp, and the menu/save screens are **never entered** from those saves. A single **shell-phase / in-encounter / menu-active save state** (DYNAMIC, local-only) unblocks GAP-0033, GAP-0034, GAP-0035, and half of GAP-0036 at once. Capturing it is the highest-leverage M6 action.

## Subsystem map
| Subsystem | Gap | Status | One-line state |
|---|---|---|---|
| Event / trigger / scripting | **GAP-0033** | In Progress (M6) | Cursor `0x800822f4` RESOLVED = resident **PRNG/noise** cursor (seeded `0x80017DB4` by [[FUNC_8005B714]]; consumed as coord-offsets/variants), NOT an event PC → [[Gameplay - Resident Event Stream]] / [[Gameplay - Resident Noise and Ctor 0x71]]. Callback dispatcher `fcn.80054964` + timer `0x800b402c` are real but the **authored event/trigger interpreter remains UNFOUND** → [[Gameplay - Events and Triggers]] |
| Enemy AI / PATH | GAP-0034 | Blocked | Relocation solved (type-dependent); `PATH*.BIN` **shelved** (0 hits/12 stages); behavior trees undecoded |
| Live warp | GAP-0035 | Blocked | Mechanism fully decoded — orchestrator [[FUNC_8005222C]] + callees; **player placement decoded** = 3-layer checkpoint/respawn ([[Gameplay - Player Spawn and Placement]]: load-spawn → [[FUNC_80054C90]] save → [[FUNC_8005B134]] restore), separate from the orchestrator. **Never executed** (crashed to BIOS mid-gameplay); needs a shell-phase fixture → [[Gameplay - Warp and Level Transition]] |
| Menu / save | GAP-0036 | Unknown | HUD draw SOLID; menu state-machine + **memory-card save** code not located (no libcard symbol) |
| Player input → movement | GAP-0037 | Needs Evidence | Player block + Y integrator mapped; **libpad read site not located** |

## Known vs unknown (static anchors)
**Shell / gameplay state machines (STATIC, CONFIRMED):** `main_shell_state_machine` `0x8004FA40` (6-way substate dispatch `jr` @`0x8004fc34`, table `0x8001b3c4`, index `[0x8008243c] mod 6`); `gameplay_state_machine` `0x8004ECD4`; globals `master_game_state 0x800823A0`, `current_scene_id 0x80082504`, `G_DAT_ENTRY_COUNTER 0x800822F0`, load/transition state `0x800822f8`. *(The dispatch tables `0x8001b3c4`/`0x8001b828` and script cursor `0x800822f4` are disasm-only, NOT in the sym file.)*

**Player (STATIC + DYNAMIC):** block `0x800A6500` (`player_x/y/z`, velocity `0x800A652C`, contact flags `0x800A6582`); movement integrator [[FUNC_8003633C]] commits collision-resolved Y at `0x80036cec` (DYNAMIC/local-only, G29). Status counters: lives `0x800a65a0`, health `0x800a7e2a`, grain `0x800a65a1`, seeds `0x800a6598/99/9a` → [[MEM - Player state 800A6500]].

**HUD (STATIC, SOLID):** [[FUNC_800526F4]] (`hud_draw`) + sub-routines `fcn.800260f8`/`fcn.80025f54`/`fcn.80026d78` → [[Menu and HUD structure]].

## Required fixtures (per subsystem)
- **GAP-0033/0034:** in-encounter / active-script save → trace cursor `0x800822f4` + timer `0x800b402c` + callback `fcn.80054964`.
- **GAP-0035:** shell-phase (pre/inter-level) save → drive the warp lever (`[0x80082504]`+`[0x8008243c]=5`).
- **GAP-0036:** shell substate sequencer **DECODED** (static, [[Menu and HUD structure]] §4a: table `0x8001b3c4`, dest-index `0x8008245c`); residual = the menu-nav cursor (telescope "continue/exit" menu is a reachable entry) + libcard/save sites.
- **GAP-0037:** **DECODED + runtime-confirmed 2026-06-21** → [[Gameplay - Input and Movement]] — pad-poll `0x8003a2dc`→`0x80039c34`→raw `0x80082412`→decode `0x800512a0`→word `0x80082488`→heading/speed→velocity `0x800a652c`. (`fcn.80055414` candidate REFUTED.)

## Likely functions / symbols
`fcn.8004fa40` (shell SM) · `fcn.8004ecd4` (gameplay SM) · `fcn.80054964` (callback dispatcher, table `0x8005494c`) · sequencer verb `0x800b3bb8` · spawner `0x80042c70` / `0x80059e44` · `0x8005222c` (warp orchestrator) · `fcn.8003cf2c` (stage loader) · chaser AI `0x8004e320` · pad-poll `0x8003a2dc`/`0x80039c34` + decode `0x800512a0` (input) · [[FUNC_8003633C]] · [[FUNC_80053814]] · [[FUNC_800586B0]]. See `symbols/re_symbols.sym` + `docs/EXECUTABLE_AND_OVERLAYS.md`.

## Carry-forward dependencies (do NOT assume solved)
- **GAP-0001** — every DYNAMIC step is local-only on the dirty fork.
- **GAP-0023** — chunk-34 **world-origin** (`WORLD_PAYLOAD_Y_OFFSET`, editor uses empirical 1450) is unresolved → needed to place event-spawned objects in world space ([[Asset - Chunk 34 Master Mesh]]).
- **GAP-0028** — camera follow-law undecoded → editor preview of *where* scripted spawns land is approximate ([[Core - Camera and Projection]]).
- **GAP-0029** — mid-level streaming/PATH is "event-gated, GAP-0033" → couples GAP-0034 to the event fixture ([[Core - CD Streaming and Caching]]).
- **GAP-0011/0038 — RESOLVED/Verified (M7 2026-06-21):** spawn-floor source = DAT via [[FUNC_80010000]] ([[Gap Audit|GAP-0011]] Verified); visual≠collision now meets the ≥2-method bar (source separation + G29 Pass-3, both arms — [[Gap Audit|GAP-0038]] Verified), **no longer single-source**. Residual = full-game *generality* ([[Gap Audit|GAP-0039]]: LEVEL02 floor confirmed per-pixel; all-stage still LIKELY) — local-only (GAP-0001).

## Proposed first experiments (local-only — cite fork state)
1. **GAP-0033 (this pass's lane):** from an active-script fixture, `accessLog` write-watch + `execTrace` cursor `0x800822f4` and timer `0x800b402c` → capture one opcode → effect. → [[Gameplay - Events and Triggers]].
2. **GAP-0035:** build a shell-phase fixture (quit/die transition) → drive the warp → unblocks multi-level fixtures for 0033/0034.
3. **GAP-0037 — DONE (static + runtime-confirmed 2026-06-21):** pad decode `0x800512a0`→word `0x80082488`→heading/speed→GTE→velocity `0x800a652c`; libpad poll `0x8003a2dc`/`0x80039c34` LOCATED. → [[Gameplay - Input and Movement]].

## M6 dependency graph
> The **event sequencer (GAP-0033)** is the likely upstream system: AI/PATH spawning, warp transitions, and gated records all route through the same script/callback machinery. The **event-state / shell-phase fixture** is the shared key. **GAP-0037 (input→movement) is the one lane that proceeds independently** (needs only an existing in-level save).

```mermaid
flowchart TD
  FIX[event-state / shell-phase fixture<br/>LOCAL-ONLY, missing]:::blk
  G35[GAP-0035 live warp]:::blkd
  G33[GAP-0033 event sequencer<br/>statically located]:::prim
  G34[GAP-0034 PATH / enemy AI]:::blkd
  G36[GAP-0036 menu / save]:::blkd
  G29[GAP-0029 event-gated streaming]
  G37[GAP-0037 input -> movement<br/>INDEPENDENT lane]:::indep
  G35 --> FIX
  FIX --> G33
  FIX --> G36
  G33 --> G34
  G33 --> G29
  classDef prim fill:#3a2a0d,stroke:#d99a2b,color:#ffe9c7;
  classDef blk fill:#3b0d0d,stroke:#e25555,color:#ffd9d9;
  classDef blkd fill:#2a0d0d,stroke:#c25;color:#ffd9d9;
  classDef indep fill:#0d2a3a,stroke:#2b8ad9,color:#c7e6ff;
```

**Depend on the fixture:** GAP-0033 (interpreter trace), GAP-0034 (PATH load), GAP-0035 (warp execution = the way to *produce* the fixture), GAP-0036 (menu/save screens). **Proceed independently now:** GAP-0037 (input→movement, [[Gameplay - Input and Movement]]) — the recommended immediate runtime lane. **Carry-forward gates (not on the critical path but needed for editor accuracy):** GAP-0023 (world-origin), GAP-0028 (camera).

## Related
[[Gameplay - Events and Triggers]] · [[Gameplay - Input and Movement]] · [[Experiment - Event Sequencer Trace]] · [[Seed planting system]] · [[Enemy relocation method]] · [[Finding - Level-warp mechanism]] · [[Menu and HUD structure]] · [[MEM - Player state 800A6500]] · [[Core - CD Streaming and Caching]] · [[Asset - Chunk 34 Master Mesh]] · [[Gap Audit]] · [[DuckStation Fork Reproducibility]]

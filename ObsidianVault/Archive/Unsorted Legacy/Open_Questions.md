---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Open Questions/Open Questions.md
aliases:
  - "Open Questions"
migration_action: archive
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Open Questions/Open Questions.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Open Questions
type: dashboard
updated: 2026-06-20
tags: [dashboard, open-questions]
---

# Open Questions

> Unresolved questions, gates, and next steps — **sorted by priority**. Each names the experiment(s) that would resolve it. Settled facts are in [[Confirmed Knowledge]]; tracked beliefs in [[Hypotheses]].
>
> **Control-document cross-reference (2026-06-20):** these questions are now also indexed by subsystem and mapped to stable gap IDs in the **§ Grouped by subsystem** table below. For the prioritized plan see **[[Roadmap]]**; for full per-gap evidence/acceptance see **[[Gap Audit]]** (GAP-0001…GAP-0043). The priority list below is preserved as-is.

## 🔴 P1 — blocking gates
1. **LZ codec — decode SOLVED; re-inject UNPROVEN** *(reconciled 2026-06-18)*. The codec is **RNC PROPACK 2.29** ([[Finding - Build toolchain and PROPACK provenance]]); the offline **decoder is byte-exact** (chunk0-validated, full file self-consistent; `tools/decode_level_raw.py` — also decodes `GFX/*.RAW`). The **recompressor is literal-only** (~1.02×, not PROPACK-equivalent) and **has never been booted on console**, so permanent disc edits of chunk 32/35/31 are *plausible but unverified*. → resolve via the **disc boot-test** (Phase 3b → [[Blocker - Recompressor cannot reproduce original compression|B14]]). RAM/save-state edits work today. See [[Finding - LEVEL.RAW is compressed]].
2. **Photogenic localized terrain pit.** A *uniform* matched lower is invisible (camera follows Y + uniform/gouraud texture); near-ground quads clip off the bottom at 512×224; the buffer is strip-ordered, not spatial. → needs the GTE-trace + frame-diff harness ([[API - execTrace]] + [[API - visual diff]] + [[API - scatterWrite]]) to calibrate model↔world scale and target a screen region. See [[G30 - Terrain render source]] · [[Finding - Localized terrain edit]].

## 🟠 P2 — would meaningfully advance the model
3. ✅ **RESOLVED (2026-06-18):** `fcn.8005b134` is an 8-way **state-handler** (jump-table `0x8001b828`, `v0∈[3,10]`), reached indirectly, **0 hits in idle play**, and **does not write player Y** — no relationship to the integrator [[FUNC_8003633C]]; the G5 "sole writer" claim is disproven. Sub-question left: what triggers states 3–10. See [[FUNC_8005B134]].
4. **Collision record→Y math residuals.** No-contact branch `0x80035210`, slide/re-test iteration, point-in-face `0x800322a0` internals, remaining record bytes. → read-watch + single-step. See [[FUNC_800345CC]].
5. **Per-plane collision granularity.** Sector-origin lever proven; a single-plane `refpt.y` lever needs a corrected winning-record capture (prior `sp+0x88` read was buggy). See [[Finding - Collision lever sector186]].
6. **Bulk-ground source pinning.** [[FUNC_80019934]]'s `s7` build-context origin is only partly traced; the multi-emitter foreground floor needs a per-emitter source trace. See [[Finding - Visible ground from DAT verts]].

## 🟡 P3 — format/semantics unknowns
7. **Payload `attr` field** (Vertex +0x8) role — UV / normal / color? And the `count≤0` head path in [[FUNC_80010000]]. See [[Finding - fcn.80010000 payload format]].
8. **LIST_B consumer** (`0x8009e338`) is write-only with no known reader. See [[FUNC_800140A0]].
9. **entry24 runtime-rewrite** (`s3` runtime ≠ static at `+0x00`) — gates static edits to that row. See [[Finding - entry24 is a culling row]].
10. **On-disk collision/sector record format** beyond the decoded fields; horizontal viewport/draw-offset mapping is not byte-exact.

## 🟢 P4 — pickup/DAT loose ends
11. **Source kind `0x31`** (appears in LEVEL03/04/05/07/09/10) — undecoded.
12. **Kinds `0x2c`/`0x2d`** (token-like) and **`0x30` telescope** (hint device) semantics beyond first-fire — unproven outside LEVEL01.
13. **FLIK "F" apparent downward visual shift** on horizontal moves — terrain grounding vs. render logic? 
14. Per-level entry-index identity maps beyond LEVEL01; LEVEL00/04/06/08 grain-count anomalies (deferred).

## 🔵 P5 — engine breadth (not yet started)
15. Controller polling (libpad) location; per-frame render-submission/flip chain; remaining BIOS thunk numbers; Option C spec coverage for non-LEVEL01.

## 🟢 Enhancements / candidate features
16. **Non-prototype 3D level editor.** Build a real editor with free camera, selectable objects, mouse/gizmo movement, and layer toggles. Feasible with current RE data for type-`0x3f` pickups, planting seeds, overlay spawns, and separate visual/collision previews. Preferred future stacks: Godot or Tauri+Three.js; PySide6 remains attractive for Python-tool integration. See [[ABL 3D Level Editor Roadmap]].
17. **Camera-aware 360° night skybox.** The current night ([[Finding - Persistent night render hook]]) draws stars/moon at fixed *screen* positions, so they don't move as the camera turns. Observed this session: the camera reorients substantially as Flik walks (loaded GTE matrix + translation both change a lot — but the GTE read is confounded by per-object matrices; the *pure* camera view matrix is in scratchpad `0x1f8003b4` / camera struct `0x800a0a64+0x28`, see [[Camera]]). FEASIBLE as an extension of the existing per-frame hook (not an overhaul). Two tiers: (a) **2D parallax** — read camera yaw/pitch, scroll the star field + moon with wraparound (light, fits the ~1000-word DMA cap); (b) **true GTE-projected skybox** — give each star/moon a fixed 3D direction, transform via the GTE each frame (needs GTE save/restore + projection-scale calibration, fewer stars). Gate: confirm the scene rotates enough to warrant it; calibrate model↔screen scale (same unknown as the localized-pit task #2). Tool: `tools/abl_night_hook.py`.

## Required-experiment map
- LZ codec → static codec finish + round-trip · Pit → [[Playbook - Trace rendering ownership]] + harness · Collision residuals → [[Playbook - Trace collision resolution]] · Structure fields → [[Playbook - Identify structure fields]] · any belief → [[Playbook - Verify a hypothesis]].

## Grouped by subsystem (audit cross-reference, 2026-06-20)
> **M5 baselines (2026-06-20):** the camera / rendering / CD-streaming / audio / video groups now have consolidated Core notes — [[Core - Camera and Projection]] · [[Core - Rendering OT and GPU Packets]] · [[Core - CD Streaming and Caching]] · [[Core - Runtime Audio Path]] · [[Core - FMV and MDEC Playback]] (GAP-0028/0030/0029/0031/0032 → In Progress; dynamic items local-only per GAP-0001).
> The same questions + the audit's newly-surfaced ones, grouped by subsystem with status / priority / related gap / next experiment. `Pn#` = the priority-list item above. Status vocab: `Unknown · Needs Evidence · In Progress · Blocked · Verified · Superseded` ([[Roadmap]] §7).

### Executable / binary
| Question | Status | Pri | Gap | Next experiment |
|---|---|:--:|---|---|
| Where do overlays' functions live (Region A/B)? | In Progress — M3 baseline complete | P2 | GAP-0020 | Use [[Executable and Overlays]]; enumerate a deeper module only when a subsystem needs it |
| No authoritative symbol map (85 reviewed baseline labels) | Verified | P2 | GAP-0018 | Maintain [[Symbol Map Baseline]]; optional live fork corroboration |
| No consolidated whole-address memory map | Verified | P3 | GAP-0019 | Capture heap/SP unknowns only when runtime evidence is available |
| Controller polling (libpad) location (P5#15) | Unknown | P3 | GAP-0037 | `execTrace` + [[API - controller input]] |
| Matching-decompilation substrate | Deferred / In Progress | P1 | GAP-0021 | Return to [[Decompilation Pilot]] only with pinned tools, object context, and modding payoff |

### Disc / filesystem
| Question | Status | Pri | Gap | Next experiment |
|---|---|:--:|---|---|
| Redump identity / checksum manifest; PAL/proto | Needs Evidence | P2 | GAP-0014 | Match Redump dat; write `Checksum Manifest.md` |
| Narrative disc/file map (only `abl.xml`) | Needs Evidence | P3 | GAP-0015 | Generate disc-map note from `abl.xml` |
| LBA-shift edits tolerated in-level? | Needs Evidence | P2 | GAP-0025 | Build an oversize edit; boot; load in-level |
| Per-level identity maps beyond LEVEL01 (P4#14) | In Progress | P2 | GAP-0039 | Deep-trace LEVEL02/03 from start-saves |

### Compression
| Question | Status | Pri | Gap | Next experiment |
|---|---|:--:|---|---|
| LZ codec re-inject: literal-only, no PROPACK encoder (P1#1) | Blocked | P2 | GAP-0024 | Public RNC encoder vs chunk0 oracle / size-budget rule |

### Rendering
| Question | Status | Pri | Gap | Next experiment |
|---|---|:--:|---|---|
| Photogenic localized terrain pit (P1#2) | Blocked | P1 | GAP-0028 | GTE-trace + frame-diff; calibrate model↔screen |
| Camera follow-law / viewport not byte-exact (P3#10) | Needs Evidence | P2 | GAP-0028 | Trace camera-matrix writer; correlate to Flik |
| OT / GPU-packet / frame-flip undocumented | Needs Evidence | P3 | GAP-0030 | Document OT + flip from [[API - gp0Trace]] |
| `fcn.800172dc`/`0x8012c1d0` mislabeled "terrain" | Needs Evidence | P2 | GAP-0010 | Re-title as shared mesh renderer |
| 360° night skybox (P-enh#17) | Needs Evidence | P3 | GAP-0028 | Read camera yaw/pitch; scroll/GTE-project stars |

### Assets / formats
| Question | Status | Pri | Gap | Next experiment |
|---|---|:--:|---|---|
| 66/69 LEVEL.RAW chunk roles unpublished | In Progress | P1 | GAP-0022 | `accessLog`/`execTrace` per-chunk consumer |
| Chunk-34 master mesh + model→world transform | In Progress | P1 | GAP-0023 | `execTrace@0x80017464`; calibrate transform |
| ~~Spawn-floor source: chunk-34/35 vs DAT?~~ **RESOLVED = DAT (`fcn.80010000`)** | ✅ Verified (M7 2026-06-21) | P1 | GAP-0011 | [[Experiment - Spawn-floor render source]] (`tools/trace_spawn_floor.py`) |
| Payload `attr` field role (P3#7) | Needs Evidence | P3 | GAP-0026 | Single-step [[FUNC_80010000]] head path |
| LIST_B consumer `0x8009e338` (P3#8) | Unknown | P3 | — | Read-watch for a reader |
| entry24 runtime-rewrite (P3#9) | Needs Evidence | P3 | — | Capture runtime `s3` vs static |
| `.ALL`/`.ANM` fine grammar; GFX CLUT exactness | In Progress | P3 | GAP-0026/0027 | Parse vertex/bone layout; trace CLUT upload |
| Pickup kinds `0x31`/`0x2c`/`0x2d`/`0x30` (P4#11–12) | Needs Evidence | P3 | — | Kind-swap + observe across levels |

### Gameplay systems
> **M6 baseline (2026-06-20):** scoped start — [[Gameplay Systems Baseline]] + [[Gameplay - Events and Triggers]] (GAP-0033: scripted-spawn sequencer statically located; turnkey [[Experiment - Event Sequencer Trace]] ready-to-run, blocked on the active-script fixture, local-only GAP-0001) + [[Gameplay - Input and Movement]] (GAP-0037 — the independent runtime lane, no event-state fixture needed). **Update:** cursor `0x800822f4` = shared byte-stream reader (no resident seed → overlay/indirect; [[MEM - Event System Globals]]); **cursor seed FOUND + LEVEL.DAT-source CORRECTED** — sole seed `0x8005b900` ([[FUNC_8005B714]] state-reset) sets `cursor = 0x80017DB4`, a **resident** EXE table (not `DATbase+K`); overlay-seed **refuted** ([[Gameplay - DAT Event Stream]]). **Table `0x80017DB4` DECODED** ([[Gameplay - Resident Event Stream]]): a ~2052 B **resident PRNG/noise table** (entropy 7.91, mean 0x80) read as zero-mean signed coord offsets + low-bit variants; consumers classified (type-0x3f/grain/contact-alloc); seed runs on scene-init (shell SM `0x8004fdf0(scene_id)`). GAP-0035 static transition model — `current_scene_id` drives handler + resource loading, per-stage loader table `0x8001afb0` decoded ([[Gameplay - Warp and Level Transition]]). **GAP-0035 spawn RUNTIME-CONFIRMED 2026-06-20**: write-watch on `0x800a6500` at LEVEL01 cold boot → writer [[FUNC_80046B20]]`(player, scene_id)` (via scene-init [[FUNC_8005B714]]), source = **resident EXE table `0x80077314`** (NOT LEVEL.DAT/LEVEL.BIN — both refuted) → [[Experiment - Initial spawn write-watch]]. **GAP-0035 warp LANDING CONFIRMED 2026-06-21**: cold-boot diversion (poke level-select `scene_table[1]`) to scene 3/6/2/4 lands cleanly at table[scene] via the same fn/table; `index==scene_id==stage`; only in-game mid-level orchestrator warp remains → [[Experiment - Warp landing diversion]].
| Question | Status | Pri | Gap | Next experiment |
|---|---|:--:|---|---|
| Resident noise cursor `0x800822f4` | RESOLVED (side-branch) | P2 | GAP-0033 | PRNG/noise table `0x80017DB4`; ctor-0x71 = **contact/proximity entity, not rendered** → jitter is contact-position variation, not visible ([[Gameplay - Resident Noise and Ctor 0x71]]) |
| **Authored event/trigger interpreter** | **VERIFIED 2026-06-21 (fully modeled)** | P2 | GAP-0033 | = the per-object **"object actor" bytecode VM [[FUNC_8004C13C]]**: **all 26 opcodes decoded/bounded** (movement op9 ← LEVEL.DAT waypoints, **player-proximity TRIGGER op17**, conditional branch op20, **native+overlay CALL op12**) + phase-2 motion + CALL sub-table + object layout; **cold-boot LEVEL01 stream captured** ([[Experiment - Mover VM cold boot opcode trace]]); **program source = RESIDENT** (table `0x80077af8`), not LEVEL.DAT. Three-lane model → [[Event and scripting system]]. Narrow residuals: 5 LIKELY ops + program-selection seed + overlay-CALL bodies |
| Level-exit / transition trigger path | **DECODED 2026-06-21** (one trigger type) | P2 | GAP-0033 | overlay verb `0x800b3e88` → `FUNC_8004A700(a3=dest)` (type-2, PROVEN call); type-6 `0x8004abf4` = per-tick countdown `[0x8008223c]`→5; dest shell-resolved `0x8004fda0` ([[Experiment - In-game warp trigger]] Pass-3 / [[FUNC_8004A700]] / [[FUNC_8004ABF4]]); open core = the *authored* interpreter above |
| Enemy AI behavior + PATH nav-graph (shelved) | Blocked | P2 | GAP-0034 | Decide dead vs decode; in-encounter save |
| Verified live warp never executed (P4) | **SPLIT 2026-06-21: 0035A arch Verified / 0035B clean handoff Blocked (shell fixture)** | P3 | GAP-0035 | **Spawn + LANDING CONFIRMED** ([[Experiment - Initial spawn write-watch]], [[Experiment - Warp landing diversion]]): [[FUNC_80046B20]]`(player, scene_id)` ← resident table `0x80077314+idx*12`; landings to scene 3/6/2/4 clean. **In-game TRIGGER LEVER CAPTURED 2026-06-21** ([[Experiment - In-game warp trigger]]): the native trigger is the transition-state var `[0x800823a0]` (resident initiators `0x800496d8/a8b4/b3c0` ← overlay scene verbs); `[0x800823a0]=6` reproducibly initiates gameplay→shell-SM→scene-init `FUNC_8005B714(a0)`. Orchestrator [[FUNC_8005222C]] is shell-only (downstream). Mid-gameplay `scene_id` pokes crash (`0xbfc02bac`, read ~15×/frame). **Pass-3 2026-06-21: overlay verb DECODED** — type-2 init `FUNC_8004A700(a3=destination)` is `jal`'d by overlay scene verbs (PROVEN); type-6 `FUNC_8004ABF4` is a per-tick countdown carrying no destination; dest shell-resolved `0x8004fda0` (force-16 when `[0x8008225c]!=0`). Clean in-game level→level **not achieved** — blocked on the shell-phase destination index + orchestrator resource sequencing |
| Menu/save state machine | Unknown | P3 | GAP-0036 | Trace menu substate `[0x8008243c]` |
| Per-plane collision granularity (P2#5) | Needs Evidence | P2 | — | Corrected winning-record capture |
| Collision record→Y math residuals (P2#4) | In Progress | P2 | — | Read-watch + single-step [[FUNC_800345CC]] |

### Audio / video
| Question | Status | Pri | Gap | Next experiment |
|---|---|:--:|---|---|
| Runtime SPU mixing/streaming path | Unknown | P3 | GAP-0031 | `execTrace` libspu during playback |
| In-engine FMV playback trigger + front-end order | Unknown | P3 | GAP-0032 | `execTrace` front-end boot; map `FMV.BIN` |

### Tooling
| Question | Status | Pri | Gap | Next experiment |
|---|---|:--:|---|---|
| Host paths in tracked tools; no deps manifest | ✅ Resolved (2026-06-21) | P1 | GAP-0003 | `_env.py` + `requirements.txt` + portability test (0 host literals) |
| No CI / GPU tests skip / codec untested | In Progress | P2 | GAP-0017/0040 | `pytest` + headless GL + round-trip test |
| Tools Catalog under-counts (38 vs 69) | Needs Evidence | P2 | GAP-0012 | Regenerate from `git ls-files tools/` |
| PsyQ version unpinned; tools unvendored | Needs Evidence | P2 | GAP-0016 | Library census; pin mkpsxiso/jpsxdec |
| Editor: pickup planner → seed/terrain layers (P-enh#16) | In Progress | P2 | GAP-0023 | Per [[ABL 3D Level Editor Roadmap]] |

### Legal / reproducibility
| Question | Status | Pri | Gap | Next experiment |
|---|---|:--:|---|---|
| Dynamic evidence rides one private fork | In Progress / operator-gated | P0 | GAP-0001 | Review/commit or patch-export dirty fork; preserve off-machine; clean-clone replay |
| Untracked inputs; findings-store overwrite hazard | In Progress | P0 | GAP-0002 | Guard + hash-pin fixtures |
| No consolidated sharing-policy note | Needs Evidence | P2 | GAP-0004 | Write `Preservation Policy.md` |
| `extracted/` not regenerable from tracked code | Needs Evidence | P2 | GAP-0005 | Commit extractors + output-hash manifest |

### Documentation
| Question | Status | Pri | Gap | Next experiment |
|---|---|:--:|---|---|
| Findings store: 2 CONFIRMED floor answers | Blocked | P1 | GAP-0008 | Mark f5/f10 Superseded; add f13 refs |
| Risk Matrix/severity stale vs notes | In Progress | P1 | GAP-0007 | Add "current tier" column |
| Occlusion fix not propagated (Home + 2 Findings) | In Progress | P2 | GAP-0009 | Add occlusion caveats |
| Legacy scorecard aligned to recorded modding-grade charter? | In Progress | P1 | GAP-0043 | Label preservation-only scoring without changing [[Roadmap]] charter |
| No project roadmap / CONTRIBUTING / owner-status | In Progress | P1/P2 | GAP-0041/0042 | This audit + `CONTRIBUTING.md` |

`P1*` / `⚖️` = scope-gated on the GAP-0043 charter decision.

## See also
[[Roadmap]] · [[Gap Audit]] · [[Project Index]] · [[Hypotheses]] · [[Confirmed Knowledge]] · [[Blockers]] (full-RE risk view) · [[Home]]

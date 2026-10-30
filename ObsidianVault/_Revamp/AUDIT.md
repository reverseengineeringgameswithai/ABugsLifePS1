---
kind: revamp_audit
created: 2026-07-08
source_state: generated_from_current_workspace
---

# Vault Revamp Audit

## Current Vault Shape

The vault currently has **350 markdown notes** and mixes Canon-like RE notes, mod notes, experiments, plans, blockers, generated API docs, and chronological handoffs in the same search space.

- `(root)`: 33 markdown notes
- `Assets`: 14 markdown notes
- `Blockers`: 26 markdown notes
- `Camera`: 1 markdown notes
- `Collision`: 1 markdown notes
- `Confirmed Knowledge`: 1 markdown notes
- `DuckStation`: 2 markdown notes
- `DuckStation API`: 41 markdown notes
- `Experiments`: 34 markdown notes
- `Findings`: 47 markdown notes
- `Fixtures`: 6 markdown notes
- `Functions`: 38 markdown notes
- `Geometry`: 5 markdown notes
- `Hypotheses`: 2 markdown notes
- `Indexes`: 7 markdown notes
- `Investigations`: 1 markdown notes
- `Memory Structures`: 19 markdown notes
- `Mods`: 2 markdown notes
- `Open Questions`: 1 markdown notes
- `Physics`: 1 markdown notes
- `Plans`: 2 markdown notes
- `Playbooks`: 13 markdown notes
- `Rendering`: 1 markdown notes
- `Save States`: 1 markdown notes
- `Symbols`: 1 markdown notes
- `Systems`: 50 markdown notes

## Major Note Categories Found

- canonical function candidate: 38
- canonical memory candidate: 19
- canonical system/finding candidate: 126
- experiment/test record: 34
- mod-specific: 2
- review/archive candidate: 32
- session log: 2
- support/index/tooling: 97

## Canonical Candidates

These notes already look like Canon inputs. They still need normalization into `Canon/` with explicit evidence/status fields; stale sections must be split away rather than copied blindly.

- `ObsidianVault/Assets/Asset - ALL ANM Format Grammar.md` — Asset - ALL ANM Format Grammar (unknown, medium)
- `ObsidianVault/Assets/Asset - Asset extraction recipe.md` — Asset - Asset extraction recipe (unknown, medium)
- `ObsidianVault/Assets/Asset - Character and plant models.md` — Asset - Character and plant models (runtime_seen, medium)
- `ObsidianVault/Assets/Asset - Chunk 34 Master Mesh.md` — Asset - Chunk 34 Master Mesh (live_confirmed, confirmed)
- `ObsidianVault/Assets/Asset - Disc file map.md` — Asset - Disc file map (unknown, medium)
- `ObsidianVault/Assets/Asset - Disc image and rebuild.md` — Asset - Disc image and rebuild (live_confirmed, confirmed)
- `ObsidianVault/Assets/Asset - GFX CLUT Exactness.md` — Asset - GFX CLUT Exactness (live_confirmed, confirmed)
- `ObsidianVault/Assets/Asset - LBA Shift Rebuild Proof.md` — Asset - LBA Shift Rebuild Proof (live_confirmed, confirmed)
- `ObsidianVault/Assets/Asset - LEVEL.BIN and overlays.md` — Asset - LEVEL.BIN and overlays (live_confirmed, confirmed)
- `ObsidianVault/Assets/Asset - LEVEL.DAT.md` — Asset - LEVEL.DAT (live_confirmed, confirmed)
- `ObsidianVault/Assets/Asset - LEVEL.RAW Chunk Role Table.md` — Asset - LEVEL.RAW Chunk Role Table (live_confirmed, confirmed)
- `ObsidianVault/Assets/Asset - LEVEL.RAW.md` — Asset - LEVEL.RAW (live_confirmed, confirmed)
- `ObsidianVault/Assets/Asset - PROPACK Rebuild Strategy.md` — Asset - PROPACK Rebuild Strategy (unknown, confirmed)
- `ObsidianVault/Assets/Assets.md` — Assets (runtime_seen, medium)
- `ObsidianVault/Collision/Collision.md` — Collision (live_confirmed, confirmed)
- `ObsidianVault/Core - CD Streaming and Caching.md` — Core - CD Streaming and Caching (live_confirmed, confirmed)
- `ObsidianVault/Core - Camera and Projection.md` — Core - Camera and Projection (live_confirmed, confirmed)
- `ObsidianVault/Core - FMV and MDEC Playback.md` — Core - FMV and MDEC Playback (live_confirmed, confirmed)
- `ObsidianVault/Core - Rendering OT and GPU Packets.md` — Core - Rendering OT and GPU Packets (live_confirmed, confirmed)
- `ObsidianVault/Core - Runtime Audio Path.md` — Core - Runtime Audio Path (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - 0x356bc is a wall not floor.md` — Finding - 0x356bc is a wall not floor (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - 0x801bdc58 is compressed source.md` — Finding - 0x801bdc58 is compressed source (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Build toolchain and PROPACK provenance.md` — Finding - Build toolchain and PROPACK provenance (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Candidate A is DAT-backed visual terrain.md` — Finding - Candidate A is DAT-backed visual terrain (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Character ALL model format.md` — Finding - Character ALL model format (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Collision RAM edit moves footing 1to1.md` — Finding - Collision RAM edit moves footing 1to1 (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Collision is planes not scalar.md` — Finding - Collision is planes not scalar (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Collision lever sector186.md` — Finding - Collision lever sector186 (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Collision on-disk source is chunk 32.md` — Finding - Collision on-disk source is chunk 32 (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Collision sector table.md` — Finding - Collision sector table (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - DAT record holds decor instance world position.md` — Finding - DAT record holds decor instance world position (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Disc rebuild is byte-exact.md` — Finding - Disc rebuild is byte-exact (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - FMV STR video replacement.md` — Finding - FMV (STR) video replacement (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - File loading is by-name (LBA-shift tolerant).md` — Finding - File loading is by-name (LBA-shift tolerant) (runtime_seen, medium)
- `ObsidianVault/Findings/Finding - Floor resource is LEVEL.RAW.md` — Finding - Floor resource is LEVEL.RAW (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - GPU primitive injection.md` — Finding - GPU primitive injection (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - LEVEL.DAT records are object paths.md` — Finding - LEVEL.DAT records are object paths (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - LEVEL.RAW is compressed.md` — Finding - LEVEL.RAW is compressed (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Level formats generalize, content is per-level.md` — Finding - Level formats generalize, content is per-level (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Level-warp mechanism.md` — Finding - Level-warp mechanism (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Live RAM probe via proc mem.md` — Finding - Live RAM probe via proc mem (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Loading screen backdrops are GFX RAW images.md` — Finding - Loading-screen backdrops are GFX/*.RAW images (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Localized terrain edit.md` — Finding - Localized terrain edit (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Longer FMV playback (normal-speed extension RE).md` — Finding — Longer FMV playback (normal-speed extension RE) (unknown, medium)
- `ObsidianVault/Findings/Finding - No static collision consumer.md` — Finding - No static collision consumer (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Pass-3 decor records decoded (cull anchor + suppression).md` — Finding - Pass-3 decor records decoded (cull anchor + suppression) (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Payload vertex edits are visible.md` — Finding - Payload vertex edits are visible (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Persistent night render hook.md` — Finding - Persistent night render hook (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Player Y writer FUNC_3633C.md` — Finding - Player Y writer FUNC_3633C (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Region-A texture format decoded.md` — Finding - Region-A texture format decoded (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - SFX replacement.md` — Finding — Sound-effect (SFX) replacement (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Sky color on-disk table.md` — Finding - Sky color on-disk table (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Sky is a GP0 background fill.md` — Finding - Sky is a GP0 background fill (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Terrain on-disk source is chunk 35.md` — Finding - Terrain on-disk source is chunk 35 (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Tier-3 render disc-delivery.md` — Finding — Tier-3 render needs its own disc file (LEVEL.DAT/RAW are LBA-full) (runtime_seen, medium)
- `ObsidianVault/Findings/Finding - Trail flag gates terrain render.md` — Finding - Trail flag gates terrain render (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Two parser source-record formats.md` — Finding - Two parser source-record formats (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Type-0x3f pickups are coordinate-moddable.md` — Finding - Type-0x3f pickups are coordinate-moddable (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - VAB sound bank format.md` — Finding - VAB sound bank format (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Visible ground from DAT verts.md` — Finding - Visible ground from DAT verts (live_confirmed, confirmed)
- ... 115 more; see `MIGRATION_MAP.md`.

## Mod-Specific Notes

These should live under `Mods/` and link to Canon functions/memory instead of redefining original-game behavior.

- `ObsidianVault/Mods/Blackberry net-new berry.md` — Blackberry / Fastberry — net-new berry (mod) (unknown, medium)
- `ObsidianVault/Mods/Gold-berry drop on non-gold kills.md` — Gold-berry drop on non-gold kills (live_confirmed, confirmed)

## Sessions / Chronological History

These should stay historical and not be treated as Canon. Copy or move only after a redirect/provenance decision.

- `ObsidianVault/Systems/AI Level - Session 2026-07-04 handoff.md` — AI Level — session 2026-07-04 handoff (unknown, medium)
- `ObsidianVault/Systems/Session 2026-07-04 - board sign + consolidated build.md` — Session 2026-07-04 — training board sign + consolidated mod build (live_confirmed, confirmed)

## Experiments / Test Records

These are evidence records. They should validate Canon claims via stable experiment IDs rather than being merged wholesale into Canon prose.

- `ObsidianVault/Experiments/Experiment - DAT relocation-aware append.md` — Experiment - DAT relocation-aware append (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Event Sequencer Trace.md` — Experiment - Event Sequencer Trace (runtime_seen, medium)
- `ObsidianVault/Experiments/Experiment - FLIK emblem image replacement.md` — Experiment - FLIK emblem image replacement (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - FLIK letters disc mod demo.md` — Experiment - FLIK letters disc mod demo (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - FLIK5 five-letter token gate.md` — Experiment - FLIK5 five-letter token gate (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G12 source vec.md` — Experiment - G12 source vec (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G13 payload v0.md` — Experiment - G13 payload v0 (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G14 payload vertex grass.md` — Experiment - G14 payload vertex grass (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G15 runtime payload vertex.md` — Experiment - G15 runtime payload vertex (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G16 emitted payload vertex wall.md` — Experiment - G16 emitted payload vertex wall (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G28 Candidate A floor Y.md` — Experiment - G28 Candidate A floor Y (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G29 Pass-3 differential.md` — Experiment - G29 Pass-3 differential (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G29 collision lever validation.md` — Experiment - G29 collision lever validation (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G30 localized terrain edit.md` — Experiment - G30 localized terrain edit (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G30 sky recolor.md` — Experiment - G30 sky recolor (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G5.5 dynamic watch.md` — Experiment - G5.5 dynamic watch (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G6 render sentinel.md` — Experiment - G6 render sentinel (runtime_seen, medium)
- `ObsidianVault/Experiments/Experiment - G8 entry24 body edits.md` — Experiment - G8 entry24 body edits (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - In-game warp trigger.md` — Experiment - In-game warp trigger (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Initial spawn write-watch.md` — Experiment - Initial spawn write-watch (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - LEVEL02 floor source.md` — Experiment - LEVEL02 floor source (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Mover VM cold boot opcode trace.md` — Experiment - Mover VM cold boot opcode trace (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Persistent nighttime render hook.md` — Experiment - Persistent nighttime render hook (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Pickup kind-swap.md` — Experiment - Pickup kind-swap (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Spawn-floor render source.md` — Experiment - Spawn-floor render source (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Starry night sky injection.md` — Experiment - Starry night sky injection (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Tier3 native FLIK letter relocation.md` — Experiment - Tier3 native FLIK letter relocation (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Tier3 native grain relocation.md` — Experiment - Tier3 native grain relocation (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Tier3 native seed token relocation.md` — Experiment - Tier3 native seed token relocation (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Training TRAINING follow-up bugs.md` — Experiment - Training TRAINING follow-up bugs (unknown, medium)
- `ObsidianVault/Experiments/Experiment - Training boot checkpoints and FMV boot buffer.md` — Experiment - Training boot checkpoints and FMV boot buffer (unknown, medium)
- `ObsidianVault/Experiments/Experiment - Training in-world TRAINING pickup word.md` — Experiment - Training in-world TRAINING pickup word (unknown, medium)
- `ObsidianVault/Experiments/Experiment - Visible floor renderer neutralize.md` — Experiment - Visible floor renderer neutralize (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Warp landing diversion.md` — Experiment - Warp landing diversion (live_confirmed, confirmed)

## Stale, Contradictory, or Suspicious Material

The vault has **109 notes** containing markers such as `wrong`, `superseded`, `stale`, `contradict`, `refuted`, `hypothesis`, `UNKNOWN`, or `TODO`. These are not necessarily bad notes, but their claims must not be promoted into Canon without review.

- `ObsidianVault/Assets/Asset - GFX CLUT Exactness.md` — Asset - GFX CLUT Exactness (live_confirmed, confirmed)
- `ObsidianVault/Assets/Asset - LEVEL.RAW Chunk Role Table.md` — Asset - LEVEL.RAW Chunk Role Table (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Assumptions Register.md` — Assumptions Register (wrong, low)
- `ObsidianVault/Blockers/Blocker - Analysis methods have systematic blind spots.md` — Blocker - Analysis methods have systematic blind spots (wrong, low)
- `ObsidianVault/Blockers/Blocker - Character and plant model formats are unreversed.md` — Blocker - Character and plant model formats are unreversed (wrong, low)
- `ObsidianVault/Blockers/Blocker - Collision internals are partly undecoded.md` — Blocker - Collision internals are partly undecoded (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - Disc provenance is unverified.md` — Blocker - Disc provenance is unverified (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - Function boundaries and overlays evade the static call graph.md` — Blocker - Function boundaries and overlays evade the static call graph (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - Headline results rest on single-source evidence.md` — Blocker - Headline results rest on single-source evidence (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - LEVEL.DAT non-pickup records are undecoded.md` — Blocker - LEVEL.DAT non-pickup records are undecoded (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - LEVEL.RAW chunk inventory is mostly unidentified.md` — Blocker - LEVEL.RAW chunk inventory is mostly unidentified (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - Offline texture and font extraction is absent.md` — Blocker - Offline texture and font extraction is absent (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - Original toolchain ground-truth is unmined.md` — Blocker - Original toolchain ground-truth is unmined (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - Project documentation is stale and contradictory.md` — Blocker - Project documentation is stale and contradictory (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - Recompressor cannot reproduce original compression.md` — Blocker - Recompressor cannot reproduce original compression (live_confirmed, low)
- `ObsidianVault/Blockers/Blocker - Struct and type recovery is shallow.md` — Blocker - Struct and type recovery is shallow (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - Symbol recovery has no authoritative map.md` — Blocker - Symbol recovery has no authoritative map (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Blocker - Training board sign disc offset unresolved.md` — Blocker - Training board sign disc byte offset unresolved (runtime_seen, confirmed)
- `ObsidianVault/Blockers/Blockers.md` — Blockers (live_confirmed, confirmed)
- `ObsidianVault/Blockers/Remediation Plan.md` — Remediation Plan (unknown, medium)
- `ObsidianVault/Blockers/Reproducibility Checklist.md` — Reproducibility Checklist (unknown, medium)
- `ObsidianVault/Blockers/Risk Matrix.md` — Risk Matrix (unknown, confirmed)
- `ObsidianVault/Camera/Camera.md` — Camera (unknown, low)
- `ObsidianVault/Collision/Collision.md` — Collision (live_confirmed, confirmed)
- `ObsidianVault/Core - CD Streaming and Caching.md` — Core - CD Streaming and Caching (live_confirmed, confirmed)
- `ObsidianVault/Core - Camera and Projection.md` — Core - Camera and Projection (live_confirmed, confirmed)
- `ObsidianVault/Core - FMV and MDEC Playback.md` — Core - FMV and MDEC Playback (live_confirmed, confirmed)
- `ObsidianVault/Core - Runtime Audio Path.md` — Core - Runtime Audio Path (live_confirmed, confirmed)
- `ObsidianVault/Decompilation Pilot.md` — Decompilation Pilot (wrong, low)
- `ObsidianVault/DuckStation/API wishlist - analysis fast-tracking.md` — API wishlist - analysis fast-tracking (static_seen, medium)
- `ObsidianVault/DuckStation API/API - camera transform.md` — API - camera transform (hypothesis, medium)
- `ObsidianVault/DuckStation API/API - code cache invalidation.md` — API - code cache invalidation (wrong, low)
- `ObsidianVault/DuckStation API/API - crash safety and health events.md` — API - crash safety and health events (unknown, low)
- `ObsidianVault/DuckStation API/API - determinism.md` — API - determinism (live_confirmed, confirmed)
- `ObsidianVault/DuckStation API/API - execTrace.md` — API - execTrace (hypothesis, medium)
- `ObsidianVault/DuckStation API/API - findings store.md` — API - findings store (live_confirmed, confirmed)
- `ObsidianVault/DuckStation API/API - framebuffer capture.md` — API - framebuffer capture (unknown, medium)
- `ObsidianVault/DuckStation API/API - gpu.pickObject.md` — API - gpu.pickObject (unknown, medium)
- `ObsidianVault/DuckStation API/API - loadState.md` — API - loadState (wrong, low)
- `ObsidianVault/DuckStation API/API - memoryScan.md` — API - memoryScan (live_confirmed, confirmed)
- `ObsidianVault/DuckStation API/API - transferLog.md` — API - transferLog (static_seen, medium)
- `ObsidianVault/DuckStation API/API - xrefs and function bounds.md` — API - xrefs and function bounds (static_seen, medium)
- `ObsidianVault/Executable and Overlays.md` — Executable and Overlays (runtime_seen, confirmed)
- `ObsidianVault/Experiments/Experiment - DAT relocation-aware append.md` — Experiment - DAT relocation-aware append (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Event Sequencer Trace.md` — Experiment - Event Sequencer Trace (runtime_seen, medium)
- `ObsidianVault/Experiments/Experiment - FLIK emblem image replacement.md` — Experiment - FLIK emblem image replacement (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - G30 localized terrain edit.md` — Experiment - G30 localized terrain edit (live_confirmed, confirmed)
- `ObsidianVault/Experiments/Experiment - Spawn-floor render source.md` — Experiment - Spawn-floor render source (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Chunk 34 master mesh structure.md` — Finding - Chunk 34 master mesh structure (wrong, low)
- `ObsidianVault/Findings/Finding - GPU primitive injection.md` — Finding - GPU primitive injection (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - LEVEL.DAT records are object paths.md` — Finding - LEVEL.DAT records are object paths (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Level-warp mechanism.md` — Finding - Level-warp mechanism (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Live RAM probe via proc mem.md` — Finding - Live RAM probe via proc mem (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Player Y writer FUNC_3633C.md` — Finding - Player Y writer FUNC_3633C (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Relocation-aware DAT append.md` — Finding - Relocation-aware DAT append (wrong, low)
- `ObsidianVault/Findings/Finding - SFX replacement.md` — Finding — Sound-effect (SFX) replacement (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Terrain on-disk source is chunk 35.md` — Finding - Terrain on-disk source is chunk 35 (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - Visible terrain renderer.md` — Finding - Visible terrain renderer (live_confirmed, confirmed)
- `ObsidianVault/Findings/Finding - fcn.80010000 payload format.md` — Finding - fcn.80010000 payload format (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_80010000.md` — FUNC_80010000 — per-object mesh draw / payload emitter (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_800140A0.md` — FUNC_800140A0 — GTE trail-cull transform (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_800172DC.md` — FUNC_800172DC — shared .ALL/mesh renderer (terrain is one occluded client) (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_8001CDC0.md` — FUNC_8001CDC0 — DAT parser / relocator (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_800345CC.md` — FUNC_800345CC — collision resolver / accumulate (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_8003CF2C.md` — FUNC_8003CF2C — resource-ID dispatcher / DAT-load caller (live_confirmed, low)
- `ObsidianVault/Functions/FUNC_80045A60.md` — FUNC_80045A60 — transition finalizer / subsystem reset (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_800526F4.md` — FUNC_800526F4 — HUD draw (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_80053814.md` — FUNC_80053814 — type-0x3f construct + contact-action dispatch (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_80054EAC.md` — FUNC_80054EAC — grain pickup handler (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_80059E44.md` — FUNC_80059E44 — ContactRecord allocator (live_confirmed, confirmed)
- `ObsidianVault/Functions/FUNC_8005B134.md` — FUNC_8005B134 — player-pos / Region-A overlay dispatcher (superseded claim) (live_confirmed, confirmed)
- `ObsidianVault/Gameplay - DAT Event Stream.md` — Gameplay - DAT Event Stream (wrong, low)
- `ObsidianVault/Gameplay - Events and Triggers.md` — Gameplay - Events and Triggers (static_seen, medium)
- `ObsidianVault/Gameplay - Input and Movement.md` — Gameplay - Input and Movement (live_confirmed, confirmed)
- `ObsidianVault/Gameplay - Player Spawn and Placement.md` — Gameplay - Player Spawn and Placement (live_confirmed, confirmed)
- `ObsidianVault/Gameplay Systems Baseline.md` — Gameplay Systems Baseline (static_seen, medium)
- `ObsidianVault/Geometry/G30 - Terrain render source.md` — G30 - Terrain render source (live_confirmed, confirmed)
- `ObsidianVault/Home.md` — Home (live_confirmed, confirmed)
- `ObsidianVault/Hypotheses/HYP - visual equals collision.md` — HYP - visual equals collision (live_confirmed, confirmed)
- `ObsidianVault/Hypotheses/Hypotheses.md` — Hypotheses (live_confirmed, confirmed)
- ... 29 more; see `MIGRATION_MAP.md`.

## Address / Function / Table Heavy Notes

**298 notes** mention specific addresses, functions, object/drop types, action IDs, tables, hooks, or globals. These are the main migration inputs for `Canon/Functions`, `Canon/Memory`, `Canon/Tables`, `Canon/Hooks`, and `Canon/Constants`.

Hot address mentions:

- `0x80010000`: 34 note/source mentions
- `0x800a7e48`: 30 note/source mentions
- `0x80036cec`: 21 note/source mentions
- `0x800172dc`: 19 note/source mentions
- `0x800a6500`: 19 note/source mentions
- `0x801607f8`: 19 note/source mentions
- `0x1f800374`: 18 note/source mentions
- `0x8012c1d0`: 18 note/source mentions
- `0x800a6504`: 18 note/source mentions
- `0x80017db4`: 18 note/source mentions
- `0x801bdc58`: 17 note/source mentions
- `0x80000000`: 17 note/source mentions
- `0x800c1688`: 16 note/source mentions
- `0x80017464`: 15 note/source mentions
- `0x8009c230`: 13 note/source mentions
- `0x80081d98`: 12 note/source mentions
- `0x800822f4`: 12 note/source mentions
- `0x800771bc`: 12 note/source mentions
- `0x80082498`: 11 note/source mentions
- `0x80082504`: 11 note/source mentions
- `0x8008240c`: 11 note/source mentions
- `0x80115aac`: 10 note/source mentions
- `0x8001a1dc`: 10 note/source mentions
- `0x80010718`: 10 note/source mentions
- `0x8001b3c4`: 10 note/source mentions
- `0x800823a0`: 10 note/source mentions
- `0x801cc390`: 9 note/source mentions
- `0x1f8003b4`: 9 note/source mentions
- `0x8004fa40`: 9 note/source mentions
- `0x80077314`: 9 note/source mentions

## Should Migrate First

- Contact object allocator/walker/drop stack: `FUNC_80059E44`, `FUNC_800586B0`, `MEM 0x800B0D18`, contact metadata tables, action dispatch.
- Enemy permanence stack: `contact_vs_actor_handler`, `0x800592A4`, `0x800a658e`, enemy death finalizer, all-defeated event.
- HUD counter stack: `FUNC_800526F4`, `0x800b0198`, `0x80082258 - 0x800a658e`.
- Gold Berry and Blackberry mod notes, but only under `Mods/`.
- Known crash/forbidden patch ranges from `src_re/known_crash_cave_hazards.c`.
- Function and memory notes that already have confirmed source C coverage.

## Should Archive or Keep Out of Canon

- Old gold-drop type-34/literal gold-berry assumptions.
- Old `0x80049958` once-per-kill hook assumption.
- Old mega-permanent claims.
- Old `0x80082030` custom descriptor/slack assumptions.
- Old visible-floor/chunk-35 claims that are superseded by DAT/`FUNC_80010000` findings.
- Planning notes, blockers, hypotheses, and session logs unless their confirmed findings are extracted.

## Needs Human Review

- Any note with strong `CONFIRMED` language but no experiment/source evidence.
- Large Tier-3/custom-level notes that mix original-game RE with mod implementation history.
- Asset/model notes that are partially decoded but still have unresolved format fields.
- Notes that depend on function boundaries or overlay call graphs derived from static analysis only.

## Generated Files

This audit is paired with:

- `ObsidianVault/_Revamp/MIGRATION_MAP.md`
- `ObsidianVault/_Revamp/CONFLICTS.md`
- `ObsidianVault/_Revamp/SRC_COVERAGE.md`
- `ObsidianVault/_Revamp/VALIDATION.md`

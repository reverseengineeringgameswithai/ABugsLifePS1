---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Indexes/_Canonical Links.md
aliases:
  - "_Canonical Links"
migration_action: merge
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Indexes/_Canonical Links.md`
- Replacement/current location: `ObsidianVault/Canon/Indexes/Canonical_Links.md`
- Archive reason: Index material should be regenerated around Canon IDs.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: _Canonical Links (note-name registry)
type: meta
updated: 2026-07-02
tags: [meta, registry]
---

# Canonical note-name registry

> Maintenance note. Every wikilink in the vault should resolve to one of these exact basenames. Keep basenames **unique** (Obsidian resolves a link by basename anywhere in the vault). When adding a note, add its name here.

## Functions/ (`FUNC_<UPPERHEX>`)
FUNC_8001CDC0 · FUNC_80053814 · FUNC_800586B0 · FUNC_80059E44 · FUNC_800526F4 · FUNC_80054EAC · FUNC_800224EC · FUNC_800140A0 · FUNC_8001DFE4 · FUNC_800172DC · FUNC_8001EA6C · FUNC_800206E8 · FUNC_80010000 · FUNC_80019934 · FUNC_8003A318 · FUNC_8001A1DC · FUNC_8003633C · FUNC_800345CC · FUNC_80025084 · FUNC_8005B134 · FUNC_80060724 · FUNC_800639CC · FUNC_80030F60 · FUNC_8003CF2C · FUNC_80046330 · FUNC_80046B20 · FUNC_8005222C · FUNC_80017B98 · FUNC_8003E928 · FUNC_8005EC94

## Findings/ (`Finding - <title>`)
Finding - Visible terrain renderer · Finding - Terrain on-disk source is chunk 35 · Finding - Collision sector table · Finding - Collision lever sector186 · Finding - Collision on-disk source is chunk 32 · Finding - Visual is not collision · Finding - Visible ground from DAT verts · Finding - Candidate A is DAT-backed visual terrain · Finding - fcn.80010000 payload format · Finding - Player Y writer FUNC_3633C · Finding - Collision is planes not scalar · Finding - Collision RAM edit moves footing 1to1 · Finding - LEVEL.RAW is compressed · Finding - Floor resource is LEVEL.RAW · Finding - 0x801bdc58 is compressed source · Finding - Trail flag gates terrain render · Finding - entry24 is a culling row · Finding - 0x356bc is a wall not floor · Finding - Payload vertex edits are visible · Finding - Sky is a GP0 background fill · Finding - Sky color on-disk table · Finding - Localized terrain edit · Finding - GPU primitive injection · Finding - Persistent night render hook · Finding - Live RAM probe via proc mem · Finding - Type-0x3f pickups are coordinate-moddable · Finding - Relocation-aware DAT append · Finding - Two parser source-record formats · Finding - No static collision consumer · Finding - Build toolchain and PROPACK provenance · Finding - Disc rebuild is byte-exact · Finding - LEVEL.DAT records are object paths · Finding - Level formats generalize, content is per-level · Finding - Level-warp mechanism · Finding - VAB sound bank format · Finding - Character ALL model format

## Experiments/ (`Experiment - <label>`)
Experiment - G5.5 dynamic watch · Experiment - G6 render sentinel · Experiment - G8 entry24 body edits · Experiment - G12 source vec · Experiment - G13 payload v0 · Experiment - G14 payload vertex grass · Experiment - G15 runtime payload vertex · Experiment - G16 emitted payload vertex wall · Experiment - G28 Candidate A floor Y · Experiment - G29 collision lever validation · Experiment - G30 localized terrain edit · Experiment - G30 sky recolor · Experiment - Starry night sky injection · Experiment - Persistent nighttime render hook · Experiment - DAT relocation-aware append · Experiment - Visible floor renderer neutralize · Experiment - FLIK letters disc mod demo · Experiment - Pickup kind-swap · Experiment - Event Sequencer Trace · Experiment - Initial spawn write-watch · Experiment - Warp landing diversion · Experiment - In-game warp trigger

## Fixtures/ (`Fixture - <name>`)
Fixture - g30 openground · Fixture - g30 openfloor · Fixture - night starry · Fixture - night live · Fixture - starry night workbench

## DuckStation API/ (`API - <name>`)
API - connection and auth · API - execution control · API - advanceUntil · API - loadState · API - saveState · API - readArray · API - scatterRead · API - scatterWrite · API - memoryScan · API - addWatch · API - accessLog · API - execTrace · API - transferLog · API - gp0Trace · API - gpu.readVramRect · API - decodeTexture · API - GTE state · API - frame capture · API - frame hashing · API - visual diff · API - snapshot bundle · API - experiment runner · API - findings store · API - symbols · API - controller input · API - determinism

## Memory Structures/ (`MEM - <name>`)
MEM - Global memory map · MEM - Terrain vertex buffer 8012C1D0 · MEM - Collision sector table 800A7E48 · MEM - Type-0x3f placement record · MEM - Contact array 800B0D18 · MEM - fcn.80010000 mesh payload · MEM - Sky DRAWENV color cache 800771BC · MEM - OT output buffer pointer 8008240C · MEM - Collision plane record · MEM - LEVEL.RAW chunk model · MEM - Parser output record · MEM - Trail and pass3 tables · MEM - Survivor lists · MEM - Player state 800A6500 · MEM - DAT runtime memory map · MEM - LEVEL.RAW chunk inventory · MEM - Skeleton bone transform 8008A1F8 · MEM - Event System Globals

## Assets/ (`Asset - <name>`)
Asset - LEVEL.DAT · Asset - LEVEL.RAW · Asset - LEVEL.BIN and overlays · Asset - Disc image and rebuild · Asset - Character and plant models · Asset - Asset extraction recipe · Asset - Disc file map · Asset - LEVEL.RAW Chunk Role Table · Asset - Chunk 34 Master Mesh · Asset - PROPACK Rebuild Strategy · Asset - LBA Shift Rebuild Proof · Asset - ALL ANM Format Grammar · Asset - GFX CLUT Exactness · Asset Extraction Pipeline

## Blockers/ (`Blocker - <title>`) — due-diligence (2026-06-18)
Blocker - Decompilation has no build or symbol substrate · Blocker - Verification is bus-factor-1 on a private emulator fork · Blocker - Headline results rest on single-source evidence · Blocker - Byte-exact disc reproduction is unproven · Blocker - Audio subsystem is completely unanalyzed · Blocker - FMV video is completely unanalyzed · Blocker - Character and plant model formats are unreversed · Blocker - RE depth is LEVEL01-only · Blocker - LEVEL.RAW chunk inventory is mostly unidentified · Blocker - LEVEL.DAT non-pickup records are undecoded · Blocker - Project documentation is stale and contradictory · Blocker - Disc provenance is unverified · Blocker - Original toolchain ground-truth is unmined · Blocker - Recompressor cannot reproduce original compression · Blocker - Symbol recovery has no authoritative map · Blocker - Struct and type recovery is shallow · Blocker - Function boundaries and overlays evade the static call graph · Blocker - Collision internals are partly undecoded · Blocker - Analysis methods have systematic blind spots · Blocker - Offline texture and font extraction is absent

## Control documents (project-level, 2026-06-20)
Roadmap · Gap Audit · Project Index · Glossary · Milestone 0 Completion · Preservation Policy · CONTRIBUTING · Checksum Manifest · Toolchain Census · DuckStation Fork Reproducibility · Symbol Map Baseline · Symbol Import Round Trip · Executable and Overlays · Decompilation Pilot

## Core engine baselines (M5, 2026-06-20)
Core - Camera and Projection · Core - Rendering OT and GPU Packets · Core - CD Streaming and Caching · Core - Runtime Audio Path · Core - FMV and MDEC Playback

## Gameplay baselines (M6, 2026-06-20)
Gameplay Systems Baseline · Gameplay - Events and Triggers · Gameplay - Input and Movement · Gameplay - Warp and Level Transition · Gameplay - Player Spawn and Placement · Gameplay - Initial Player Spawn · Gameplay - DAT Event Stream · Gameplay - Resident Event Stream · Gameplay - Resident Noise and Ctor 0x71

## Hubs / Dashboards / Indexes / Playbooks
Home · README · Confirmed Knowledge · Open Questions · Hypotheses · Blockers · Risk Matrix · Assumptions Register · Remediation Plan · Reproducibility Checklist · Tools Catalog ·
Systems · Collision · Rendering · Geometry · Camera · Physics · Assets · Memory Structures · Playbooks · ABL Level Editor · ABL 3D Level Editor Roadmap · Blender-first ABL level editor ·
G29 - Collision source · G30 - Terrain render source ·
Functions Index · Findings Index · Experiments Index · Fixtures Index · DuckStation API Index · Symbols Index · Gap Priorities ·
LEVEL.DAT object pipeline · Geometry pipeline · Menu and HUD structure ·
Retail Gameplay Completeness Gap Audit · Campaign Level Coverage Matrix · Editor Visual Fidelity Baseline · Level Goal and Exit Trigger Matrix ·
Playbook - Trace rendering ownership · Playbook - Trace collision resolution · Playbook - Find geometry sources · Playbook - Identify structure fields · Playbook - Verify a hypothesis · Playbook - Follow a pointer chain · Playbook - Correlate rendering and collision · Playbook - Create a deterministic experiment

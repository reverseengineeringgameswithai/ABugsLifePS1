---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Glossary.md
aliases:
  - "Glossary"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Glossary.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Glossary
type: reference
updated: 2026-06-21
tags: [reference, glossary, onboarding]
---

# Glossary

> Project-specific and general reverse-engineering / PS1 terms used across this vault. General terms are kept short; **project-specific** terms link to the authoritative note. See also [[README]] (conventions) and [[Project Index]] (navigation).

## Reverse-engineering & decompilation
- **Disassembly** — turning machine code (MIPS R3000A here) back into assembly mnemonics. Here via **radare2** with `anal.gp=0x80081d98`. No persisted disasm DB yet (GAP-0018).
- **Decompilation** — reconstructing higher-level C from machine code. This project has ~6–8 functions with real C bodies (`src_re/*.c`); the rest are behavioral notes. See **matching**.
- **Matching (matching decompilation)** — C that, recompiled with the *original* toolchain/flags, produces **byte-identical** machine code (verified with a diff tool like `objdiff`/`asm-differ`). The gold standard for preservation. **Not currently done** — there is no build/diff substrate (GAP-0021, [[Blocker - Decompilation has no build or symbol substrate|B1]]). Contrast *behavioral RE* (understand what code does, without byte-matching).
- **Behavioral RE** — establishing what code/data does via tracing + experiments, without reconstructing matching C. The project's actual mode.
- **Symbol map** — a table mapping addresses → names (functions, globals). Here a hand-maintained [[Symbols Index]] (~90 of ~1,070); no machine-readable `re_symbols.sym` committed (GAP-0018, [[Blocker - Symbol recovery has no authoritative map|B15]]).
- **Memory map** — a map of what occupies each RAM region. Scattered across [[Memory Structures]] notes; no consolidated whole-address-space map yet (GAP-0019).
- **Executable** — the main program. Here **`SCUS_942.88`** (471,040 B PS-X EXE), load address `0x80010000`, entry `0x8005F690`, text size `0x72800`, runtime `$gp = 0x80081d98`. See `docs/EXECUTABLE_AND_OVERLAYS.md`.
- **Overlay** — code/data swapped into a fixed RAM region at runtime (PS1 had no MMU/paging). ABL uses **Region A `0x800b39a0`** (per-level `LEVEL0N\LEVEL[M].BIN`) and **Region B `0x800b5788`** (`BITS\MEMORY.BIN`, `FMV\FMV.BIN`). Not yet disassembled (GAP-0020, [[Blocker - Function boundaries and overlays evade the static call graph|B17]]).
- **`$gp` (global pointer)** — a MIPS register holding a base address so globals are reached as `[gp+offset]` in one instruction. Here `0x80081d98`; assumed correct (A3) — errors cascade into mis-resolved globals.
- **r2 / radare2** — the disassembler/analysis framework used; the `i`/`afl`/`om` outputs are the static basis (A3).
- **Counterfactual** — a controlled change whose *predicted* effect is observed (e.g. edit a value → the screen changes as predicted). Required for `CONFIRMED` per [[API - determinism]].

## PlayStation 1 hardware & SDK
- **GTE (Geometry Transformation Engine)** — the PS1's COP2 fixed-point 3D math coprocessor (matrix transforms, perspective projection, lighting). The game's vertices are transformed by it; readable live via [[API - GTE state]].
- **MVMVA** — a GTE op computing `M·V + T` (matrix × vector + translation). ABL skins character vertices rigidly with one `MVMVA` per vertex (24-bone skeleton → [[Finding - Character ALL model format]]).
- **RTPS / RTPT** — GTE "perspective transform single/triple" ops that project 3D vertices to screen + depth, used by the mesh emitter [[FUNC_80010000]].
- **Ordering Table (OT)** — a reverse-linked list the GPU walks back-to-front for painter's-order rendering; primitives are inserted by depth. ABL's OT pointer is [[MEM - OT output buffer pointer 8008240C]] (format note pending, GAP-0030).
- **GPU packet / primitive** — a command word + data the GPU draws (flat/gouraud/textured tri/quad, fill, etc.). ABL's floor uses GP0 `0x3C` (gouraud quad); arbitrary packets can be **injected** ([[Finding - GPU primitive injection]]).
- **GP0 / GP1** — the GPU's two command ports: GP0 = drawing/transfer commands (e.g. `0x02` fast-fill = the sky, [[Finding - Sky is a GP0 background fill]]); GP1 = display control.
- **DRAWENV / DISPENV** — PsyQ drawing/display environment structs (draw area, offset, background clear). The sky colour lives in a DRAWENV cache [[MEM - Sky DRAWENV color cache 800771BC]].
- **VRAM** — the GPU's 1 MB framebuffer (1024×512 16-bit) holding the frame + textures + CLUTs; readable via [[API - gpu.readVramRect]].
- **TIM** — the standard PS1 image file format (pixel data + optional CLUT + VRAM coordinates). *Note:* ABL's images are **PROPACK-packed `GFX/*.RAW`**, not loose TIMs; CLUTs are uploaded separately (GAP-0027).
- **CLUT (Color Look-Up Table)** — a palette for 4/8-bpp images, stored in VRAM. ABL CLUTs are ripped from VRAM, not yet decoded from disc (GAP-0027).
- **tpage (texture page)** — a 256×256 VRAM region textures are addressed within; part of the Region-A texture decode ([[Finding - Region-A texture format decoded]]).
- **SPU (Sound Processing Unit)** — the PS1 audio chip (24 ADPCM voices + reverb). ABL audio formats are decoded; the runtime SPU path is not RE'd (GAP-0031).
- **VAB / VH / VB** — PsyQ sound-bank format (`.VH` header + `.VB` body of SPU-ADPCM **VAG** samples). ABL uses a compact `pBAV` v6 variant → [[Finding - VAB sound bank format]].
- **VAG** — a single SPU-ADPCM sample (the unit inside a VAB).
- **XA (CD-XA ADPCM)** — audio streamed directly off the CD, interleaved with data; used for ABL music/ambience (8 stereo channels @ 37.8 kHz), extracted via jpsxdec. See [[Blocker - Audio subsystem is completely unanalyzed|B5]].
- **MDEC (Motion DECoder)** — the PS1's hardware JPEG-like decoder for full-motion video. ABL FMV is `.STR`/MDEC (e.g. `INTRO` 320×128, 1750 frames), extracted via jpsxdec. See [[Blocker - FMV video is completely unanalyzed|B6]].
- **STR** — the PS1 streaming-video container (MDEC frames + interleaved XA audio).
- **libpad / libgte / libgpu / libspu / libcd** — PsyQ SDK libraries (controller, geometry, graphics, sound, CD). Library identification is a cheap symbol-seeding route (GAP-0016).
- **PsyQ** — Sony's official PS1 C SDK/toolchain (`ccpsx`, `psylink`). ABL was built with PsyQ + SN Systems **PsyMake 1.11** → [[Finding - Build toolchain and PROPACK provenance]].

## Disc, filesystem & build
- **Sector** — the CD's smallest addressable unit. PS1 CD-ROM = **2352 bytes/sector** raw (Mode2/2352 here), with **2048 B** user data in Mode2/Form1, **2336 B** in Form2 (XA/STR). ABL disc = **313,897 sectors** / 738,285,744 B.
- **LBA (Logical Block Address)** — a sector's absolute index from the disc start. ABL files have fixed LBAs in `REBUILD/abl.xml` (e.g. `LEVEL01/LEVEL.DAT` @ LBA 2906). File loading is **by-name** (LBA-shift tolerant for the EXE boot) → [[Finding - File loading is by-name (LBA-shift tolerant)]].
- **EDC / ECC** — error-detection/correction codes in each CD sector; must be regenerated correctly on rebuild (verified byte-exact, [[Finding - Disc rebuild is byte-exact]]).
- **ISO 9660** — the CD filesystem; the volume here is `A_BUGS_LIFE`, boot `cdrom:\SCUS_942.88;1`.
- **mkpsxiso / dumpsxiso** — the tools that rebuild / extract a PS1 disc from/to an XML manifest. ABL uses **mkpsxiso 2.20** + `REBUILD/abl.xml`; unpatched round-trip = **byte-exact**.
- **jpsxdec** — third-party tool that decodes PS1 STR/XA/TIM media. Used for ABL FMV + XA extraction (vendored under `jpsxdec_v2.1-beta/`, gitignored).
- **Redump** — the preservation-grade disc-dump database/standard. ABL's master is **not yet matched** to a Redump entry (GAP-0014, [[Blocker - Disc provenance is unverified|B12]]).
- **Checksum** — a short value computed from data to detect corruption (e.g. **CRC32** `607704bb` for the ABL `.bin`).
- **Hash** — a fingerprint of data; here **MD5** (`2c3861a3…`) / **SHA-1** (boot-EXE `af43de22…`) used to pin provenance and verify rebuilds.
- **Reproducibility** — the ability for *another* person/machine to re-derive a result. The project's `CONFIRMED` rubric *requires* it; today most dynamic results are reproducible only on one host (GAP-0001, [[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]]).
- **Asset pipeline** — the chain from disc → extracted/decoded asset → (optionally) edited → repacked → rebuilt disc. ABL's is solid for LEVEL.DAT pickups; gated on a PROPACK encoder for compressed assets (GAP-0024).

## Project-specific: ABL files & formats
- **LEVEL.DAT** — the per-level **uncompressed** object/placement file (disc==RAM). Holds **type-0x3f** pickup records + 10 other record types (object paths). Parsed once at load by [[FUNC_8001CDC0]] (relocates 1248 baked offsets). → [[Asset - LEVEL.DAT]].
- **LEVEL.RAW** — the per-level **compressed** geometry+collision resource: **69 chunks** in 3 regions (textures / sprites+seeds / geometry). Decompressed by [[FUNC_8001A1DC]]. → [[Asset - LEVEL.RAW]], [[MEM - LEVEL.RAW chunk inventory]].
- **chunk** — one PROPACK frame inside LEVEL.RAW (`[size header][packed data]`). Key ones: **31** = seeds, **32** = collision planes, **34** = master mesh, **35** = terrain mesh. 66/69 roles still `LIKELY` (GAP-0022).
- **PROPACK (RNC ProPack 2.29)** — the **R**ob **N**orthen **C**ompression LZ packer used for LEVEL.RAW + `GFX/*.RAW`. Decoder is **byte-exact**; only a *literal* re-encoder exists (GAP-0024). → [[Finding - LEVEL.RAW is compressed]].
- **type-0x3f / type-3F** — the LEVEL.DAT record class for **pickups/placeable objects** (0x10 bytes; runtime position = file value `<<5`). The shipped modding target (move/add). → [[MEM - Type-0x3f placement record]], [[Finding - Type-0x3f pickups are coordinate-moddable]].
- **kind (byte)** — within a type-0x3f record, selects the object's model **and** behavior (e.g. `0x14` grain, `0x30` telescope). Proven by the kind-swap demo → [[Experiment - Pickup kind-swap]].
- **sector table (collision)** — the runtime collision structure at `0x800a7e48` (223 × 0x30) built from LEVEL.RAW chunk 32; the floor is a set of **planes**, not a scalar height. → [[MEM - Collision sector table 800A7E48]], [[Finding - Collision is planes not scalar]].
- **Candidate A** — the LEVEL.DAT mesh payload (DAT `0x188cc`) shown to deform the **visible** floor (G28). Central to the visual≠collision result — now corroborated by the **M7 G29 Pass-3 counterfactual** (both arms; GAP-0038 Verified), and the chunk-34 tension is **resolved** (visible spawn floor = DAT; chunk-34/35 = occluded/collision-adjacent — GAP-0011). → [[Finding - Candidate A is DAT-backed visual terrain]].
- **visual ≠ collision** — the project's headline: the terrain you *see* and the floor you *stand on* are different files/RAM/code. → [[Finding - Visual is not collision]].
- **`.ALL` / `.ANM`** — the bespoke Iguana/TT **model** (`.ALL` = position-independent primitive list) and **animation** (`.ANM` = 24-bone skeletal, bitmask keyframes) formats; one grammar covers all actors/props/plants/terrain meshes. → [[Finding - Character ALL model format]], [[MEM - Skeleton bone transform 8008A1F8]].
- **PATH\*.BIN** — `PAD\PATH*.BIN` files presumed to hold an enemy/AI nav-graph; **never observed loaded** in 12 stages + ~10 enemies → shelved (GAP-0034). → [[Blocker - Collision internals are partly undecoded|B18]].
- **seed (planting system)** — plantable seeds are a **separate** system from type-0x3f pickups (live handle + rooted/grown flags), sourced from LEVEL.RAW chunk 31. → [[Seed planting system]].

## Project-specific: tools, harness & method
- **DuckStation external-debugger API** — the project's **custom (non-upstream) DuckStation fork** exposing a JSON-RPC debugger: VRAM readback, `gpu.pickObject`, GTE state, frame-diff, `accessLog`/`execTrace`/`transferLog`, `movie`, `experiment.run`, findings store. The entire dynamic-evidence layer depends on it (B2). → [[DuckStation API Index]].
- **fixture** — a saved game state (`.sav`) or movie you load to reproduce a scenario (e.g. `Fixture - g30 openground`). The reproducibility unit. → [[Fixtures Index]].
- **findings store** — `src_re_geometry/re_findings_backup.yaml`, the machine-readable claims DB. **Footgun:** `findings.save` overwrites → always `findings.load` first (GAP-0002). The earlier visible-floor contradiction is **resolved** — **f13 is the sole CONFIRMED** floor answer (GAP-0008, M7 2026-06-21). → [[API - findings store]].
- **determinism rubric** — the project's acceptance standard for `CONFIRMED` (reproducible **and** causal). → [[API - determinism]].
- **confidence vocabulary** — the controlled grades attached to every claim: **CONFIRMED** (reproducible **and** causal — a counterfactual or ≥2 independent methods) · **LIKELY** (single uncontrolled but consistent evidence) · **INVESTIGATING** · **UNKNOWN** · **DISPROVEN** / **SUPERSEDED** (retracted/replaced; kept for history, link the replacement). A single uncontrolled snapshot is at most LIKELY; *screenshots corroborate, they don't prove*. → [[API - determinism]], [[Roadmap]] §6, [[CONTRIBUTING]].
- **local-only evidence** — a result that reproduces **only on the operator's machine** because it rides the private DuckStation fork + host-local `.sav` fixtures (GAP-0001/0002). Recorded honestly as local-only, never promoted to third-party-reproducible `CONFIRMED`; the standing reproducibility ceiling on every dynamic finding. → [[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]], [[DuckStation Fork Reproducibility]].
- **phase-matched control** — when frame-diffing an *animated* subject, a control run at the same animation phase, so the diff flags only the change (not the animation). A hard-won method baked into [[API - experiment runner]].
- **neutralize / MOVE / RECOLOR test** — experiment styles: *neutralize* (suppress a draw call to see what vanishes — blind to camera-locked uniform terrain), *move/recolor* (perturb a value and watch the screen). The neutralize blind spot is [[Blocker - Analysis methods have systematic blind spots|B19]].
- **G-series (G1…G30)** — the numbered geometry-RE experiment arc (`src_re_geometry/geometry_g*.md`) that answered the visual-vs-collision question.
- **B-series (B1…B20)** — the due-diligence **[[Blockers]]** catalog. **GAP-000N** — the stable IDs in **[[Gap Audit]]** that map onto B-series + new gaps.

## See also
[[Project Index]] · [[Roadmap]] · [[Gap Audit]] · [[Open Questions]] · [[Confirmed Knowledge]] · [[DuckStation API Index]] · [[README]] · [[Home]]

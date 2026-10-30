---
kind: experiment
id: EXP_2026-08-03_phase4_e01_terrain_visual
status: complete
source_state: original_game
system: [SYS_world_render_dispatch, FUNC_80010000]
row: E01_terrain_visual
---

# Phase 4 E01: terrain visual geometry — render-path synthesis + campaign node survey

## Question

E01_terrain_visual's scope: the complete per-level source/consumer/material/culling/
animation model. The Tier-3 and level-editor campaigns had already solved most of the
consumer side for LEVEL01 without the row citing any of it, and the row's own `next` was a
directly executable offline step: "Extend the payload map beyond LEVEL01 — run the extractor
across all 10 level dirs."

## Render path, assembled from committed Canon

**Source**: LEVEL.DAT node arrays — 0x18-stride records: `T_obj` world anchor (+0/4/8), a
per-run constant class marker (+0x10), payload file offset (+0x14) pointing at an
`fcn.80010000` vertex payload. Proven for LEVEL01 (node_base `0x45F0`); placement law
`world = T_obj + v_local`, no Y-flip.

**Consumer**: `FUNC_80010000` (RTPT `0x800106F8`) with the exact solved transform on the
committed MEM_8012C1D0 page — `world = (R⁻¹·(TR + RT·v/4096) + Cdiv)×32` via scratchpad
camera struct `0x1F800374`, validated by exact forward-projection. Dispatched from the frame
driver's jalr render tail (`SYS_world_render_dispatch`, suppression-proven live).

**A stale row binding corrected**: the row framed "shared vertex arena 0x8012C1D0 (chunk
34/35)" as terrain. The committed MEM page's own correction banner refutes this — at render
time that buffer holds Flik's FLICK.ALL (1032 RTPT hits = only Flik, two levels tested);
chunk-34/35 is never drawn. The binding now carries the correction instead of the
superseded claim.

**Materials**: per-face texpage decoded offline; VRAM page↔chunk map built once from live
LEVEL01 capture (LEVEL01-only — named residual). **Culling**: `FUNC_80014360` pass-3
backdrop cull; pass-3 XYZ = cull anchor. **Round-trip**: LEVEL01 rebuilt byte-identical
from JSON (committed Canon) — the source model is reproduction-complete, not read-only.

## The campaign node survey (new, offline)

`tools/phase4_e01_node_survey.py` scans all 21 campaign DATs for 0x18-stride runs with a
repeated nonzero `+0x10` constant and strictly-increasing in-file payload offsets. Key
design point discovered en route: **the marker constant is per-level/per-class, not
global** — assuming LEVEL01's `0xC0080000` found runs in only 4 of 21 DATs; discovering the
marker per run found primary arrays everywhere. The scanner hard-fails unless it
re-discovers LEVEL01's proven `0x45F0`×42 ground truth (it does, exactly).

Primary runs: L00 `0x16A0`×38 · L01 `0x45F0`×42 · L02 `0x1630`×81 · L03/L1 `0x1CE0`×31 ·
L04 `0x78EC`×77 · L05 `0x6710`×97 · L06 `0x3A1C`×72 · L07 `0x4A68`×211 · L08 `0x5E98`×182 ·
L09 `0x3E48`×42 · L10 `0x36BC`×55. Markers form a systematic family (`0xC00X0000`,
X∈{4,6,7,8,9}) — constant within a run, varying by record class; LEVEL01 alone carries six
classes in adjacent runs. Hypothesis (undecoded): a packed class/vertex-format word.

Cross-checks: the committed extractor already decodes type-0x3f objects cross-level
(LEVEL02: 60 objects) but 0 meshes outside LEVEL01 — this survey supplies exactly the
missing per-level node_base/count candidates. Noise honestly flagged: LEVEL05/L1 and
LEVEL08/L1 produce dozens of short non-family-marker runs (other structures matching the
shape); LEVEL04's secondary DATs have no candidates.

## The animation question, answered (2026-08-03, "dig deeper")

Per the operator's "dig deeper to get your answer" — does terrain animation exist at all?

**Method**: idle-diff VRAM. Three scenes loaded, zero input, full-VRAM snapshots diffed per
32×32 cell at intervals. The churn classifies cleanly: the double-buffered framebuffer pair
(mirrored blocks exactly 512 apart, sized by how much on-screen motion the idle scene has);
a relocating 64×128 streaming-upload signature (same shape, different x per level —
character/effect texture streaming); and CLUT/HUD rows. Then a focused pass on LEVEL01's
terrain-page band (pages 0–11), hashing every cell 5× at 30-frame intervals: **187/192
cells byte-stable (97.4%)**; four page-10 cells stream forward (all-distinct contents — the
signature again); and exactly **one cell cycles** — `(256,32)` in page 4, contents repeating.

**The join that names it**: against the extractor's LEVEL01 decode, that tile is sampled by
exactly **52 faces, all inside one dedicated `scenery_surface` payload (`@0x4c1a4`)** whose
faces repeatedly map the same 64×64-texel rect. No other mesh touches it.

**Answer**: terrain/scenery animation exists in exactly one identified form — **flipbook
tile re-upload driving a single dedicated water-like scenery surface**. Everything else is
byte-stable while idling; no CLUT-cycling observed. Plausible (untraced) mechanism: the
already-Canon 0x22-chunk animation-strip pipeline (the training-word letter system) reused
for scenery tiles. Frame count ≥4; exact cycle length aliased by the 30-frame sampling.

## What's still open

Per-level payload decode validation (profiles for the editor stack — the survey provides
the bases); marker-word semantics; materials beyond LEVEL01; the animated-tile **uploader**
call site and disc source (0x22-chunk hypothesis, not traced) plus campaign breadth of
animated tiles; the flagged noise runs; whether LEVEL1.DAT primary runs are floors or
overlay-scene decor.

## Reproduction

```bash
python3 tools/phase4_e01_node_survey.py   # stdlib-only, self-checking
python3 -m pytest -q tests/test_phase4_e01_terrain_visual.py
```

## Evidence

`analysis/phase4_e01_terrain_visual.json`, `analysis/phase4_e01_node_survey.json`,
`tools/phase4_e01_node_survey.py`; committed Canon cited inside the artifact.

## 2026-08-04 Phase 4 closure addendum

**Disposition:** PARTIAL, SUBSTANTIATED, BOUNDED-EXHAUSTED.

This addendum closes the prior animated-tile gap and corrects the earlier node-marker interpretation. The machine-readable result is analysis/phase4_e01_closure.json.

### Method and escalation boundary

1. Relevant retained capsules were checked first. None retained the LEVEL01 0x80089638 tile-data table, 0x80096B98 descriptor table, or the loaded source node needed for these questions.
2. Static work used C against the pristine retail ASM listings and all campaign LEVEL*.RAW, LEVEL*.DAT, and LEVEL*.BIN inputs.
3. DuckStation was used only for the named missing domain: the exact live descriptor/data pointers and CPU-to-GPU transfer for LEVEL01 tile 125.
4. The live run used a fresh isolated config at /tmp/abl-phase4-e01-20260804, port 23601, pristine SCUS-94288 media, and hash-pinned level01.sav.
5. No input movie and no cold boot were required because no executable, disc, or asset was changed.

### Confirmed animated-texture path

**Static observation**

- 0x8003B830 handles LEVEL.RAW subtype 0x22: it stores chunk+8 in 0x80089638[tile] and clears the alternate slot at 0x80095138[tile].
- 0x80026DF4 selects the strip and live tile descriptor, derives destination X/Y and dimensions, advances to frame * width * height / 2, and calls GPU upload helper 0x800628C0.
- Gameplay update call 0x8004F13C invokes 0x80056F68, the ambient tile-124/tile-125 driver.
- Tile 125 uses frame byte 0x800A65A6 and countdown 0x800A65A7. With the exact 0x80045678(player) gate false it resets/uploads frame 0. With the gate true, expiration consumes script/RNG bytes to select delay (byte & 7)+3 and frame (next_byte & 3)+2, so frames 2 through 5 recur at intervals of 3 through 10 driver ticks.
- 0x80045678 is kept structurally named: it matches the player pointer in eight slots at 0x80089860, rejects a missing or -1 slot, and returns byte bit 2 from 0x800894B0. No broader gameplay label is inferred here.

**C campaign census**

- 228 subtype-0x22 strips occur in 18 campaign RAW files; the retail decompressor port reported zero decode errors.
- LEVEL01 contributes 13 strips. Tile 125 is the 40x19, 9-frame strip used below.
- All 20 campaign LEVEL*.BIN overlays were scanned for direct JALs to the uploader and its wrappers.
- Six direct overlay uploader calls were found: LEVEL03/L1 tile 51; LEVEL04 tile 50; three LEVEL07/L1 calls including tile 50 and one dynamic tile; and one dynamic LEVEL08/L1 call. No direct wrapper call was found. This bounds the exceptional scene-owned animation path separately from the resident common driver.

**Runtime causal confirmation**

- Tile 125 data pointer: 0x800C0928, hence subtype-0x22 chunk base 0x800C0920.
- Descriptor pointer: 0x8008209C; bytes 100028130400703a0c260000.
- The uploader event at frame 12519/cycle 7088121283 was a0=125, a1=0, a2=5, ra=0x800571D0.
- The same frame produced GP0 A0 CPU-to-VRAM at cycle 7088212268 with destination (259,38), size 10x19 VRAM pixels/words, and header words A0000000 00260103 0013000A.
- That rectangle intersects the previously observed coarse (256,32) animated cell. This is instruction-to-transfer causality, not only a visual/hash correlation.

### Correction: 0xC0080000 is not a node-class marker

The generalized node survey remains useful for locating repeated 0x18 source records, but its semantic label is superseded.

For the non-bit3 source record, pristine 0x8001CDC0 establishes:

    +0x00  s32 vec[3]
    +0x0C  s16 angle[3]
    +0x12  s16 unk12
    +0x14  u32 payload pointer/file offset
    size   0x18

Therefore the word at +0x10 packs angle[2] in its low half and unk12 in its high half. LEVEL01 0xC0080000 is {angle[2]=0, unk12=-16376}. The parser passes only angle[0..2] to confirmed rotation-matrix setup 0x80017B98; it does not read unk12 on the non-bit3 path.

Two independent bounds reject invented semantics:

- The C payload probe found no marker relation to vertex count or payload span.
- Mesh command-stream texture pages do not follow the high-half 4/6/7/8/9 family, rejecting the texture-page hypothesis.
- A live read watch at LEVEL01 runtime 0x80164DF8 recorded zero reads over frames 12528 through 12591. This places the word outside the steady-state render loop, but does not claim it is never consumed during load/zone construction.

The exact downstream meaning of non-bit3 unk12 remains unknown. Resolving it would require load/build provenance or controlled mutations across representative records. That is a low-return semantic field, not a missing trigger or control-flow edge for E01.

### Why E01 is bounded-exhausted

The source formats, retail relocation/parser path, visible render path, animated strip loader/uploader, LEVEL01 recurrence, exact GPU destination, and campaign breadth are now evidenced. Remaining work is bounded to:

- naming non-bit3 unk12;
- visually naming every campaign payload/material;
- classifying short secondary-DAT false-positive runs;
- expanding primary/secondary DAT floor-versus-decor labels when an editor or named behavior actually requires them.

Those are catalog-expansion or dormant-field questions. They do not block reproduction or explanation of the Phase 4 E01 behavior, so the row remains honestly partial but is sufficiently substantiated and bounded-exhausted to move on.

### Reproducible artifacts

- tools/phase4_e01_animation_probe.c
- tools/phase4_e01_overlay_callscan.c
- tools/phase4_e01_marker_census.c
- tools/phase4_e01_marker_payload_probe.c
- tools/phase4_e01_datbase_xrefs.c
- analysis/phase4_e01_animation_probe.json
- analysis/phase4_e01_overlay_callscan.json
- analysis/phase4_e01_closure.json

Transient evidence and hashes are enumerated in the closure JSON. The isolated DuckStation PID was stopped through its owned config directory after clearing instrumentation and controller state.

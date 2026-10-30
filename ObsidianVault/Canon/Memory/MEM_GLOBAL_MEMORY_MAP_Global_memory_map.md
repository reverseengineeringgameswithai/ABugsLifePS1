---
kind: memory
id: MEM_GLOBAL_MEMORY_MAP
aliases: [MEM_GLOBAL_MEMORY_MAP, "MEM - Global memory map"]
address: multiple
name: Global_memory_map
status: static_seen
confidence: medium
source_state: original_game
system: []
read_by: []
written_by: []
related_structs: []
evidence: []
src_paths: []
patch_policy: do_not_touch
---

# MEM_GLOBAL_MEMORY_MAP - Global memory map

## Purpose

Consolidated M3 address-axis view for SCUS-94288 USA V1.0. Confidence is per row. It combines the independently read PS-X EXE header with `docs/EXECUTABLE_AND_OVERLAYS.md`, existing `MEM -`/`FUNC_` notes, and read-only local overlay metadata. No executable, overlay, RAM dump, or save state is committed.

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - Global memory map
type: memory
updated: 2026-06-20
confidence: MIXED — per-row
tags: [memory, executable, overlays, milestone3, gap-0019]
---

# MEM — Global PS1 memory map

> Consolidated M3 address-axis view for SCUS-94288 USA V1.0. Confidence is per row. It combines the independently read PS-X EXE header with `docs/EXECUTABLE_AND_OVERLAYS.md`, existing `MEM -`/`FUNC_` notes, and read-only local overlay metadata. No executable, overlay, RAM dump, or save state is committed.

## Source executable identity

| Fact | Value | Confidence / evidence |
|---|---|---|
| File | `SCUS_942.88`, 471,040 B | **Verified** — owner-local `REBUILD/files/SCUS_942.88`, ignored |
| SHA-1 / MD5 | `af43de22474f15664d0e17498fbd27faeb7ed111` / `5848df330a0e4583dcfdd22d1fe9b0ff` | **Verified** locally; matches [[Checksum Manifest]] |
| PS-X EXE magic | `PS-X EXE` | **Verified** at file offset 0 |
| Payload mapping | file `0x800` → VA `0x80010000`, size `0x72800`, end-exclusive `0x80082800` | **Verified** from header + file length |
| Entry PC | `0x8005F690` | **Verified** from header |
| Header GP | `0x00000000` | **Verified** from header; runtime GP is set by crt0 |
| Runtime GP | `0x80081D98` | **Verified** by resident disassembly/existing traces |
| Header stack | base `0x801FFFF0`, offset 0 | **Verified** from header |
| `SYSTEM.CNF` stack | `0x801FFF00` | **Verified** from disc manifest content as recorded in executable docs; differs from header |
| Header data/BSS fields | all zero | **Verified** from header; does not describe the crt0-cleared BSS below |

## Address axis

| Range / address | Owner / role | Confidence | Evidence / caveat |
|---|---|---|---|
| `0x80000000–0x801FFFFF` | 2 MiB cached main-RAM mirror | **Verified** project platform baseline | Uncached mirror at `0xA0000000`; precise kernel-reserved low-RAM use is **Not confirmed from current repo contents.** |
| `0x80010000–0x800827FF` | resident executable payload | **Verified** | PS-X EXE header and file mapping |
| `0x8005F690` | `entry0` crt0 | **Verified** | sets GP/SP, clears BSS, enters `0x8004FA40` |
| `0x80081D98` | runtime `$gp` anchor | **Verified** | [[Symbols Index]], disassembly recipes |
| `0x80082200–0x800B399F` | crt0 zero-fill/BSS range | **Verified from disassembly** | Header BSS fields are zero. Range overlaps the resident payload tail `0x80082200–0x800827FF`; treat the code-derived clear as authoritative but preserve this warning. |
| `0x800822F0–0x80082508` | GP-relative parser/render/scene globals | **Verified / mixed roles** | `G_DAT_ENTRY_COUNTER`, pass pointers, scene state, OT ptr, DAT base; see [[Symbol Map Baseline]] |
| `0x80089528` | matrix LUT | **Needs Evidence** role; address stable | [[Symbols Index]] |
| `0x80096B98` | 128-entry object pointer list | **Verified** | overlay init / executable docs |
| `0x80096DA0` | dynamic DAT type-pointer table | **Verified** | [[FUNC_8001CDC0]] |
| `0x8009C230` | collision-candidate list | **Verified** | [[MEM - Collision sector table 800A7E48]] |
| `0x8009C870` | 8 × `0x344` visual sprite-object pool | **Verified** | executable docs / rendering notes |
| `0x800A6500…` | player position/progress block | **Verified** | [[MEM - Player state 800A6500]] |
| `0x800A7E48` | 223 × `0x30` collision sector table | **Verified** | [[MEM - Collision sector table 800A7E48]] |
| `0x800B0D18` | 64 × `0x38` contact/pickup records | **Verified** | [[MEM - Contact array 800B0D18]] |
| `0x800B39A0–0x800B5787` | Region A overlay swap buffer (`0x1DE8` capacity) | **Verified base/capacity from full file inventory** | per-level `LEVEL0N/LEVEL*.BIN`; largest file ends exactly at Region B base; current file determines occupied extent |
| `0x800B5788–0x800BE5E7` | Region B with `BITS/MEMORY.BIN` | **Verified file/base/extent** | 36,448-byte module; known init `0x800BD518` |
| `0x800B5788–0x80131EEF` | Region B with `FMV/FMV.BIN` | **Verified file/base/contiguous size; entry unknown** | 509,800-byte module; time-swapped with `MEMORY.BIN` |
| `0x800C1688` | on-disk sky-color source table | **Verified** | [[MEM - Sky DRAWENV color cache 800771BC]] |
| `0x800C1690` and `~0x800D0xxx` | collision-plane blocks/records | **Verified examples; allocator-wide extent unknown** | [[MEM - Collision plane record]] |
| `0x80115AAC–0x801CC68F` | compressed LEVEL.RAW load (`0xB6BE4`) | **Verified for LEVEL01** | [[MEM - LEVEL.RAW chunk model]]; per-level sizes differ |
| `0x8012C1D0–0x8012E784` | active/shared mesh vertex buffer (chunk 35 in the documented LEVEL01 load) | **Verified address/range; role naming has historical contradictions** | [[MEM - Terrain vertex buffer 8012C1D0]], GAP-0010 warning |
| `0x801607F8–0x801B1C0F` | in-place LEVEL01 `LEVEL.DAT` image (`0x51418`) | **Verified for LEVEL01** | [[MEM - DAT runtime memory map]] |
| `0x80161CFC` | trail/pass-1 block within DAT | **Verified** | [[MEM - Trail and pass3 tables]] |
| `0x801642E4` | pass-3 block within DAT | **Verified** | same |
| `0x801B1C10–0x801B588F` | parser output records (484 × `0x20`) | **Verified for LEVEL01** | [[MEM - Parser output record]] |
| `0x801CC390` / `0x801E134C` | observed display/OT double-buffer region anchors | **Needs Evidence as full allocation bounds** | rendering findings; do not treat either as a general heap limit |
| near `0x801FFF00–0x801FFFF0` | initial stack top | **Verified competing configuration values** | header vs `SYSTEM.CNF`; runtime selection after boot is **Not confirmed from current repo contents.** |

## Other PS1 address spaces used

| Address | Role | Confidence |
|---|---|---|
| `0x1F800000…` | scratchpad; camera/view scratch observed at `0x1F800374`, `0x1F800384`, `0x1F8003B4` | **Verified addresses; semantic names provisional** |
| `0x1F801000…` | hardware I/O | **Verified platform baseline** |
| `0x1F801810` / `0x1F801814` | GPU GP0 / GP1 | **Verified platform baseline** |
| BIOS vectors `0xA0`, `0xB0`, `0xC0` | BIOS call gates | **Verified**; `0x80065EEC` is the A0:39 `InitHeap` thunk |

## Heap and overlay cautions

- `InitHeap` is called, but the exact heap start/end arguments are **Not confirmed from current repo contents.** Do not label all RAM above resident BSS as one heap.
- Overlay addresses are valid only while the corresponding module is loaded. Region A and B labels must be interpreted with scene/media state.
- LEVEL.RAW and LEVEL.DAT ranges are LEVEL01 observations, not universal fixed bases/sizes for every stage.
- The header's zero BSS fields and the code-derived clear range are not the same evidence source; this note preserves both instead of silently choosing one.

## Commands used (read-only)

```bash
python3 -c 'import hashlib,struct,pathlib; p=pathlib.Path("REBUILD/files/SCUS_942.88"); b=p.read_bytes(); print(len(b), hashlib.sha1(b).hexdigest(), hashlib.md5(b).hexdigest(), struct.unpack_from("<8I", b, 0x10))'
r2 -2 -q -a mips -b 32 -e cfg.bigendian=false -m 0x800b39a0 ... LEVEL.BIN
sha1sum REBUILD/files/{SCUS_942.88,LEVEL01/LEVEL.BIN,LEVEL01/LEVEL1.BIN,BITS/MEMORY.BIN,FMV/FMV.BIN}
```

The abbreviated r2 command is expanded exactly in [[Executable and Overlays]].

## Related

[[Symbol Map Baseline]] · [[Executable and Overlays]] · [[Symbols Index]] · [[MEM - DAT runtime memory map]] · [[MEM - LEVEL.RAW chunk model]] · [[MEM - Player state 800A6500]] · [[MEM - Collision sector table 800A7E48]] · `docs/EXECUTABLE_AND_OVERLAYS.md`


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - Global memory map.md`
- Migration status: copy-first Canon seed.

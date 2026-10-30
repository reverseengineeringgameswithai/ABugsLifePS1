---
kind: experiment
id: EXP_2026-07-08_chunk_load_evidence
name: LEVEL.RAW chunk runtime load evidence (69/69)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_function_census]
fixtures: [from-boot-movie-level01]
artifacts: [analysis/level_raw_chunks.json, tools/chunk_evidence.py]
---

# EXP_2026-07-08_chunk_load_evidence

## Question
Which LEVEL.RAW chunk loads where at runtime, requested by whom — promoting
the statically-classified chunk role table (GAP-0022) to load-evidenced
records? (Old blocker B9's remaining ask.)

## Method
`tools/chunk_evidence.py`: join the 121 captured decompressor calls
([[EXP_2026-07-08_boot_trace_baseline]], watch on `FUNC_8001A1DC` capturing
a0/a1/a2/ra) against the byte-exact chunk table
(`tools/LEVEL_RAW_decompressed/chunk_index.json`). Src/dst classified
empirically per call (the argument inside the compressed image window
`0x80115AAC..+0xB6BE4` is the source); src offsets mapped to chunk boundaries
with ≤0x20 header tolerance.

## Observations
- **69/69 chunks matched a runtime decompress call at exact chunk-boundary
  alignment**; 20 leftover calls are other LZ containers (GFX/*.RAW loading
  screens), correctly unmatched.
- **Every chunk is requested from `ra=0x8003a4ec`** — the subtype dispatch
  drives the whole chunk pipeline.
- Destination cross-validation against known ground truth is exact:
  - ch32 → `0x800c1688` = the documented sky-table/collision arrival address;
  - ch35 → `0x8012c1c4` = the mesh vertex buffer `0x8012C1D0` minus its
    12-byte header.
- New load addresses (previously unknown): ch33 → `0x800fb418`,
  ch34 → `0x800ff97c`, and the full per-object mesh arena enumeration
  ch36–68 (`0x8012f6b8` … `0x8015fcbc`).
- Texture chunks 0–14 decompress into a **staging buffer at `0x800b5790`
  (Region B base+8)** before VRAM upload — Region B doubles as the level-load
  texture staging area, which explains why texture chunks never appear at
  stable RAM addresses.

## Conclusion
`analysis/level_raw_chunks.json` is the committed, regenerable chunk
load-evidence table: all 69 chunks now carry runtime `load_address` +
`loader_caller` + frame. The stale B9 claim ("~66 of 69 unidentified") is
fully superseded: roles were already classified statically (GAP-0022), and
load evidence is now runtime-proven. Remaining for full consumer-level
CONFIRMED on ch33/36–68: trace who READS each destination (a per-chunk
accessLog pass — future work, cheap now that destinations are known).

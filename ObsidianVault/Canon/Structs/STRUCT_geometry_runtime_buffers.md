---
kind: struct
id: STRUCT_geometry_runtime_buffers
created: 2026-07-08
updated: 2026-07-08
status: static_seen
confidence: medium
source_state: original_game_reference_or_mod_reference
src_paths:
  - src_re_geometry/geometry_runtime_buffers.c
address: 0x00730182
patch_policy: safe_to_read
---

# STRUCT_geometry_runtime_buffers - geometry runtime buffers

## Purpose

This page closes the migration source-coverage gap for `src_re_geometry/geometry_runtime_buffers.c`. It records the symbol `ParserRuntimePtrs_G3` and links the C reference into the structured vault.

- Address if known: `0x00730182`
- Coverage comments: original address header: caller fcn.8003cf2c (level/resource loader) call site @0x8003d568;; structs: ParserRuntimePtrs_G3


## C source excerpt

Source: `src_re_geometry/geometry_runtime_buffers.c`

```c
/* ============================================================================
 * geometry_runtime_buffers.c  —  Runtime geometry buffers        [PHASE G3 — ANALYZED 2026-06-13]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : caller fcn.8003cf2c (level/resource loader) call site @0x8003d568;
 *                    producer fcn.8001cdc0 (parser). This file catalogs the runtime BUFFERS
 *                    and resolves the pass-1 output-array address relationship for LEVEL01.
 * CONFIDENCE       : Buffer RELATIONSHIPS (output base = DATbase+arg2; arg2 = file-reader retval;
 *                    return = (pass1+pass3)<<5; the 0x1180 reserve mismatch) are CONFIRMED by
 *                    disassembly. ABSOLUTE addresses depend on the runtime DATbase and are LIKELY
 *                    (DATbase = 0x801607f8 corroborated by one doc note). Struct ROLES UNKNOWN
 *                    (G4/G5). C body = ANNOTATION ONLY.
 * SOURCE NOTES     : r2 disasm of SCUS_942.88 fcn.8003cf2c (G3, read-only),
 *                    src_re/dat_parser_8001cdc0.c (Phase 1), dat_geometry_records.c (G2),
 *                    docs/DAT_FORMAT_AND_RELOCATION.md (DATbase note), docs/GEOMETRY_RE_PLAN.md (G3).
 * KNOWN CALLERS    : N/A (data catalog).
 * KNOWN CALLEES    : N/A.
 * KNOWN GLOBALS    : G_DAT_BASE_PTR(0x80082498), G_TRAIL_BLOCK_PTR(0x800824ac),
 *                    G_PASS2_BASE_PTR(0x80082338), G_PASS3_BASE_PTR(0x80082508),
 *                    G_DAT_ENTRY_COUNTER(0x800822f0), gp+0x604(0x8008239c, epilogue out_end-tail).
 * UNRESOLVED       : concrete DATbase (heap cursor [sp+0x98] in the caller); whether arg2 is exact
 *                    file size or sector-padded; role of the 0x1180 reserved gap; payload-band roles.
 *
 * ============================================================================
 * CALLER ANALYSIS — fcn.8003cf2c -> fcn.8001cdc0 (CONFIRMED by disasm)
 * -------------------------------------------------------------------
 * The DAT-load case sets DATbase to the current heap cursor, reads the file there, then calls the
 * parser with arg2 = the number of bytes the file-reader returned:
 *
 *   0x8003d49c  sw   zero, 0x9c(sp)
 *   0x8003d4a0  lw   v0,   0x98(sp)        ; v0 = heap/resource cursor (call it C0)
 *   0x8003d4ac  sw   v0,   0x2498(at)      ; [0x80082498] = C0   -> DATbase := cursor
 *   ...
 *   0x8003d548  lui  a1, 0x8008
 *   0x8003d54c  lw   a1, 0x2498(a1)        ; a1 = DATbase
 *   0x8003d550  jal  0x80046330           ; fcn.80046330(path=sp+0x10, dest=DATbase) -> v0 = bytes read
 *   0x8003d554  addiu a0, sp, 0x10
 *   0x8003d558  move a0, s4                ; a0 = s4 (IGNORED by parser)
 *   0x8003d55c  lw   v1, 0x98(sp)          ; v1 = C0
 *   0x8003d560  move a1, v0                ; a1 = arg2 = bytes read  (== DAT file size)
 *   0x8003d564  addu v1, v1, a1            ; v1 = C0 + filesize
 *   0x8003d568  jal  0x8001cdc0           ; parser(a0=ignored, a1=arg2=filesize)
 *   0x8003d56c  sw   v1, 0x98(sp)          ; [delay] cursor := C0 + filesize
 *   0x8003d570  lw   v1, 0x98(sp)
 *   0x8003d578  addu v1, v1, v0            ; v1 = (C0+filesize) + parser_retval
 *   0x8003d57c  sw   v1, 0x98(sp)          ; cursor := C0 + filesize + parser_retval
 *
 * CONCLUSIONS (CONFIRMED):
 *  - arg2 is NOT a constant/global: it is the file-reader's return (bytes loaded == DAT size).
 *  - output base = DATbase + arg2 = the address immediately AFTER the loaded DAT.
 *  - caller consumes the parser return value (entries<<5) to advance its heap cursor.
 *
 * ============================================================================
 * CONCRETE LEVEL01 BUFFER MAP (relationships CONFIRMED; absolutes LIKELY via DATbase)
 * ---------------------------------------------------------------------------------
 *   filesize          = 0x51418                       (CONFIRMED, pristine DAT)
 *   DATbase           = 0x801607f8                    (LIKELY; doc note file 0x468 -> VA 0x80160c60)
 *   arg2              = filesize = 0x51418            (CONFIRMED = reader retval; padding UNKNOWN)
 *   output base       = DATbase+arg2 = 0x801b1c10     (CONFIRMED relationship)
 *   pass1 written     = 484 * 0x20 = 0x3c80           (CONFIRMED count*stride)
 *   written end       = 0x801b5890
 *   parser return     = (484+140) << 5 = 0x4e00       (CONFIRMED; counts pass1+pass3)
 *   reserved end      = output base + 0x4e00 = 0x801b6a10
 *   *** MISMATCH ***  = 0x4e00 - 0x3c80 = 0x1180 = 140*0x20  (pass-3 entries counted but NOT written
 *                       by pass 1; the caller reserves 0x1180 bytes the parser left uninitialized).
 *
 * Runtime layout (LIKELY absolutes):
 *   [0x801607f8 .. 0x801b1c10)  loaded LEVEL.DAT (0x51418)
 *      file 0x1500 end of records          -> 0x80161cf8
 *      G_TRAIL_BLOCK_PTR  (file 0x1504)    -> 0x80161cfc
 *      G_PASS2_BASE_PTR   (file 0x3ae8)    -> 0x801642e0   (empty: [p2]=-1)
 *      G_PASS3_BASE_PTR   (file 0x3aec)    -> 0x801642e4
 *      source-record band (file 0x45f0..0x8bd8)  -> 0x80164de8 .. 0x801693d0
 *      payload band       (file 0x8bd8..0x4f32c) -> 0x801693d0 .. 0x801afb24  (INSIDE the DAT)
 *   [0x801b1c10 .. 0x801b5890)  PASS-1 ParserOutputRecord20[484]  (WRITTEN)
 *   [0x801b5890 .. 0x801b6a10)  reserved gap (0x1180, role UNKNOWN)
 *   [0x801b6a10 .. )            next resource (heap cursor)  <-- G18 GUESSED floor here; RETRACTED by G26
 *                                                               (0x801bdc58 = compressed LEVEL.RAW source, not floor)
 *
 * NOTE: the source records' relocated sub-pointers (+0x14/+0x1c) target the payload band, which is
 * WITHIN the loaded DAT (file offsets < filesize). So pass-1 output records (matrices) live AFTER
 * the DAT, but the geometry source records and their payloads live INSIDE the DAT image.
 *
 * ============================================================================
 * G18 ADDENDUM (2026-06-14) — "next resource" region holds a runtime/heap floor payload
 * --------------------------------------------------------------------------------------
 * The G17 Candidate B runtime log (EXEC 0x800108b4, broad walkable floor view) found the emitted
 * floor/top-surface payload at runtime base 0x801bdc58 (a0=0x801bdc5c at the packet-store gate; all
 * 17 hits = one payload). Address placement:
 *     0x801bdc58 - DATbase(0x801607f8)      = 0x5d460   -> INVALID DAT offset (> filesize 0x51418)
 *     0x801bdc58 - EOF(0x801b1c10)          = 0xc048    -> output-buffer offset
 *     0x801bdc58 - reserved end(0x801b6a10) = 0x7248    -> INTO the "next resource" heap region
 * So the walkable floor is NOT the loaded DAT, NOT the pass-1 matrix output buffer, and NOT the
 * reserved gap -- it is 0x7248 into whatever resource loads after the parser output.
 *
 * WHY IT CANNOT BE A LEVEL.DAT PAYLOAD (CONFIRMED):
 *   - fcn.8001cdc0 (parser) is called ONCE (jal @0x8003d568) -> LEVEL.DAT parsed once; no heap
 *     source records from a 2nd parse.
 *   - ALL 1248 LEVEL.DAT relocation targets are in [0x45f0, 0x4f32c] (tools/dat_reloc.py); max
 *     0x4f32c << the floor's required 0x5d460. So no parser-relocated pointer can equal 0x801bdc58.
 *   - The emitter loads a0 DIRECTLY from the source record with NO base add:
 *         0x80020684  lw a0,0x1c(s2)     ; or
 *         0x80020694  lw a0,0x20(s2)
 *     so [s2+0x1c]/[s2+0x20] already holds the ABSOLUTE payload address. For the floor that field
 *     holds a heap pointer the parser did not (could not) write -> written at runtime by a generator,
 *     OR s2 itself is heap-resident.
 *
 * SEPARATE LEVEL01 TERRAIN RESOURCES (LIKELY source of the floor): besides LEVEL.DAT (the parsed
 * object/geometry DAT = walls/grass/props), LEVEL01 ships LEVEL.RAW (0xb68e4), LEVEL1.RAW (0x84210),
 * TERRAIN.ALL (0x39d8c) and TERR1.ALL (0xf078); TERRAIN.ALL/TERR1.ALL begin with s16 coordinate-pair
 * streams (terrain mesh, NOT in the fcn.80010000 {u32 count; Vertex 0xc; cmds} payload format ->
 * converted/decompressed into a heap payload at runtime). Executable references the names (izz:
 * level.raw/level1.raw/..., bits\plantter.all, terr1, .all). The "next resource" region is where such
 * a resource lands. Exact resource + generator = UNKNOWN until a WRITE watch on 0x801bdc58 during load.
 *
 * GUARDRAIL: do NOT treat 0x5d460 as a DAT offset; do NOT patch runtime-buffer addresses; the floor is
 * NOT a LEVEL.DAT vertex (no LEVEL.DAT edit moves it). Collision/pathing UNKNOWN (visual != collision).
 * Full trace + runbook: src_re_geometry/geometry_g18_output_buffer_floor_trace.md.
 *
 * ============================================================================
 * G19 ADDENDUM (2026-06-14) — the loader parses MULTIPLE DATs; floor is LIKELY a SECOND parsed DAT
 * --------------------------------------------------------------------------------------------------
 * REPRODUCIBILITY: the floor payload 0x801bdc58 is OBSERVED ONCE / NOT REPRODUCIBLE (no conditional BP in
 * DuckStation); the reproducible nearby hit is DAT decor 0x2d460 (rt 0x8018dc58). Pivot from re-hitting a0
 * to identifying the floor RESOURCE/SOURCE. Full detail: src_re_geometry/geometry_g19_floor_resource_source.md.
 *
 * CORRECTION to the G18 ADDENDUM above ("parser fcn.8001cdc0 is called ONCE -> LEVEL.DAT parsed once;
 * no heap source records from a 2nd parse"): that is the SINGLE STATIC CALL SITE (0x8003d568), NOT a runtime
 * guarantee. The call site lives inside fcn.8003cf2c, a RESOURCE-ID DISPATCHER (jump table 0x8001afb0, 17
 * handlers) with FOUR callers (0x8003f544/0x800503cc/0x80052290/0x8005b830). So the parser EXECUTES ONCE PER
 * DAT LOADED and can run multiple times per level. A SECOND parsed DAT (LEVEL1.DAT 0x1a568 / LEVEL2.DAT
 * 0x40784, both present in LEVEL01/ and both parser-format) loaded after LEVEL.DAT is relocated against ITS
 * OWN heap base, so ITS payload pointers land in the 0x801bxxxx region -- exactly where the floor 0x801bdc58
 * lives. LEVEL1.DAT/LEVEL2.DAT CONTAIN wide-flat floor-signature payloads in the exact fcn.80010000 format
 * (LEVEL.DAT does not). (G18's "floor not in the LEVEL.DAT image at 0x801607f8" and "all 1248 LEVEL.DAT reloc
 * targets < 0x4f32c" still hold -- those bound the FIRST DAT only.)
 *
 * SHARED LOAD+PARSE BLOCK (CONFIRMED disasm): handlers converge on ~0x8003d2f0..0x8003d570:
 *   0x8003d4ac  sw v0,0x2498(at)     ; DATbase ([0x80082498]) := heap cursor for THIS load
 *   0x8003d550  jal fcn.80046330     ; file read (a0=path sp+0x10, a1=DATbase dest) -> v0 = bytes read
 *   0x8003d568  jal fcn.8001cdc0     ; parse THIS dat (a1 = filesize)
 * The exact 2nd-DAT base is UNKNOWN: none of 0x801b1c10 / 0x801b5890 / 0x801b6a10 makes 0x801bdc58 a clean
 * payload in LEVEL1/LEVEL2.DAT, so an intervening load/alignment shifts the base. PROPOSED narrow runtime
 * check (no a0 reproduction): EXEC BP at 0x8003d550 + 0x8003d568, log (filename -> base, size) for every
 * resource at LEVEL01 load; the DAT whose [base,base+size) contains 0x801bdc58 owns the floor (offset =
 * 0x801bdc58 - base). Alternative: WRITE-watch 0x801b6a10 during load.
 *
 * ============================================================================
 * G20 ADDENDUM (2026-06-14) — loader trace ran: parser ONCE; floor source = terrain .all loader (non-parser)
 * --------------------------------------------------------------------------------------------------------
 * The G19 runbook was executed: EXEC 0x8003d550 and EXEC 0x8003d568 each hit ONCE during "Loading Level...",
 * a1=0x51418 at the parse = LEVEL.DAT. So fcn.8001cdc0 runs EXACTLY ONCE for LEVEL01. This REFUTES the G19
 * H1 ("floor = a second parsed DAT via fcn.8001cdc0") and re-vindicates the G18 "parser once" claim. The
 * floor must come from a NON-PARSER loader.
 *
 * Static map of the 14 fcn.80046330 file-reads (G20): only 0x8003d550 feeds the parser; the rest bypass it.
 * PRIME non-circular floor source = the POST-DAT TERRAIN .all loader:
 *   fcn.8005d654 (sidecar load loop, 16 callers, indexes object table 0x800a6300)
 *     -> fcn.8002ffa8 (builds "<name>.all" from name table 0x80082128=".all"/0x80082138="terr1"/
 *                      0x80082150="terrain"; file-read 0x8002ffe4 to [s0]=heap dest)
 *     -> fcn.8002fce8 (processes the .all s16 (x,z) stream into 0x4c-stride records at 0x80098a8a)
 * The orchestrator loads each terrain slot into a HEAP CURSOR [s1] and advances it -- the same pattern that
 * left LEVEL.DAT's cursor at 0x801b6a10, so the terrain .all data lands in the 0x801bxxxx region where the
 * floor 0x801bdc58 sits. TERRAIN.ALL(0x39d8c)/TERR1.ALL(0xf078) are s16 (x,z) streams (NOT verbatim payloads;
 * 0x7248 is not a payload in either), so the floor mesh is RUNTIME-GENERATED from them. H2 (terrain .all ->
 * generated floor) is now LEADING; H1 REFUTED; H3 (decompressed LEVEL.RAW; candidate high-heap loader
 * 0x8003a388 -> dest ~0x801cc390) open/lower. NEXT runbook (no a0 repro): EXEC 0x8002ffe4 (+0x80030dc0), log
 * a0(filename)/a1(dest)/size; test a1 <= 0x801bdc58 < a1+size. Full detail:
 * src_re_geometry/geometry_g20_sidecar_loader_trace.md.
 *
 * ============================================================================
 * G21 ADDENDUM (2026-06-14) — terrain .all BPs did NOT fire; watch the file-loader ENTRY fcn.80046330
 * ----------------------------------------------------------------------------------------------------
 * The G20 runbook was run: EXEC 0x8002ffe4 and EXEC 0x80030dc0 each hit 0 times during LEVEL01 load. So the
 * G20 "terrain .all = prime target / H2 leading" framing is REFUTED (downgraded to open/unconfirmed). Two
 * CONFIRMED reasons call-site BPs miss the floor load: (a) orchestrator fcn.8005d654 SKIPS the file-read
 * when terrain is already resident (0x8005d76c bnez v0,0x8005d794 -> processor fcn.8002fce8 runs, no load);
 * (b) the high-heap loader fcn.8003a318 (file-read 0x8003a388) is reached INDIRECTLY (no direct jal), so no
 * call-site BP catches it.
 *
 * fcn.80046330 is the UNIVERSAL file loader: fcn.80046330(a0 = bare filename string, a1 = destination base)
```

Note: source excerpt truncated; 324 additional lines remain in `src_re_geometry/geometry_runtime_buffers.c`.

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
 * -> v0 = bytes read (s0=a0, fp=a1; it prepends the CD/level dir and reads to a1). All 14 file-read call
 * sites funnel through it. CALLER MAP (14 sites -> 11 fns): #1 0x8003d550 fcn.8003cf2c = LEVEL resource
 * dispatcher (builds level<N>.<ext>; loads all level*.dat/raw/bin; fired LEVEL.DAT x1 0x51418); #2/#10
 * memory.bin -> 0x800b5788; #3/#4 terrain .all (0 hits); #6 0x8003a388 fcn.8003a318 HIGH-HEAP loader, dest
 * 0x801cc390 - align(size) top-down (indirect = PRIME); #7 fixed 0x800b39a0; #8/#9 FMV; #11/#12 audio;
 * #13 fixed 0x80095398; #14 .anm. fcn.8003a318 region can CONTAIN the floor 0x801bdc58 for files >=0xe738
 * that fit above the DAT (e.g. TERR1.ALL 0xf078 -> [0x801bd318,0x801cc390)).
 *
 * NEXT RUNBOOK (one BP, broad-but-narrow, no a0 repro): EXEC 0x80046330 -> log a0(filename C-string),
 * a1(dest), ra(caller->subsystem), v0(size via one-shot BP at ra); test a1 <= 0x801bdc58 < a1+size to find
 * the floor's source file/offset. If none brackets it through load->gameplay, floor is cached/boot-generated
 * -> arm 0x80046330 from the title screen, or watch processor EXEC 0x8002fce8. Full detail:
 * src_re_geometry/geometry_g21_file_read_caller_map.md.
 *
 * ============================================================================
 * G22 ADDENDUM (2026-06-14) — FLOOR SOURCE RESOURCE = LEVEL.RAW (high-heap load brackets 0x801bdc58)
 * --------------------------------------------------------------------------------------------------
 * The G21 runbook (EXEC 0x80046330) caught it. Hit #4 (ra=0x8003a390 = indirect high-heap loader
 * fcn.8003a318): dest a1=0x80115aac, size v0=0xb6be4, range [0x80115aac,0x801cc690) -> BRACKETS the floor
 * 0x801bdc58 at source offset 0xa81ac. SOURCE FILE = LEVEL.RAW (CONFIRMED by size+dest): fcn.8003a318 sets
 * dest = 0x801cc390 - align(filesize); 0x801cc390 - 0x80115aac = 0xb68e4 = LEVEL.RAW's EXACT logical size
 * (bytes-read 0xb6be4 = +0x300 sector padding); no other sidecar within 200KB. Hit #6 control = LEVEL.DAT
 * (a1=0x801607f8), does not bracket. Hit #4 precedes Hit #6, so LEVEL.RAW loads FIRST to 0x80115aac, then the
 * DAT (0x801607f8) + parser output (..0x801b6a10) overwrite the lower-middle; the floor 0x801bdc58 sits ABOVE
 * the DAT EOF/reserved-end in the SURVIVING upper part of the LEVEL.RAW buffer.
 *
 * NOT VERBATIM/EDITABLE AT 0xa81ac: LEVEL.RAW[0xa81ac] u32=0x70d4001a (impossible vertexCount) -- it's an
 * indexed-geometry STREAM (incrementing indices), not the fcn.80010000 {u32 count; vertex 0xc; cmds} format.
 * The floor emitted a VALID payload at runtime, so runtime[0x801bdc58] != disk LEVEL.RAW[0xa81ac] -> the floor
 * is CONVERTED/GENERATED from LEVEL.RAW at runtime (confirms the G18 "runtime-generated floor", now NAMES the
 * source file). fcn.8003a318 loads LEVEL.RAW then inits global tables (8/0x81-entry arrays at 0x800a65b0/
 * 0x8009fc10/0x80095138/0x80098638) -- a resource-setup fn; the buffer is consumed by the geometry converter.
 *
 * RECOMMENDATION (Option A, no patch): read-only decode of LEVEL.RAW's geometry format around 0xa81ac (vertex
 * pool, index grammar) toward an eventual LEVEL.RAW-format edit (NEVER a LEVEL.DAT edit); + one deterministic
 * confirm at Hit #4 (read a0 C-string = "level.raw"; read 0x801bdc58 right after load, compare to
 * LEVEL.RAW[0xa81ac]=1a 00 d4 70). Do NOT patch 0xa81ac (processed resource). Full detail:
 * src_re_geometry/geometry_g22_high_heap_floor_source.md.
 *
 * ============================================================================
 * G23 ADDENDUM (2026-06-15) — LEVEL.RAW is COMPRESSED; "processed" = decompression by fcn.8001a1dc
 * --------------------------------------------------------------------------------------------------
 * Decoding LEVEL.RAW around 0xa81ac: it is COMPRESSED data (window [0xa8000,0xa8400) = 213 distinct bytes/1024,
 * high entropy; s16 reads are noise; a FULL-FILE scan finds 0 clean fcn.80010000 payloads). The G22 high-heap
 * loader fcn.8003a318 calls fcn.8001a1dc = an LZ/Huffman bitstream DECOMPRESSOR:
 *   0x8003a4c8 lw fp,0x588(gp)   ; fp = [gp+0x588] = decompressed-output dest
 *   0x8003a4e0 move a0,s5        ; a0 = LEVEL.RAW base 0x80115aac (COMPRESSED input)
 *   0x8003a4e4 jal 0x8001a1dc    ; decompress(a0=src, a1=fp dst)
 *   0x8003a4ec lw s4,(fp)        ; read decompressed header
 * fcn.8001a1dc (span 0x8001a1dc..0x8001a8f8) traits: full register-context save/restore (all GPRs incl k0/k1/gp);
 * big-endian control-word fetch (lbu x4 + <<24/16/8|); bit-by-bit flag reader (t2=t2+t2; t7=t2>>8; andi t7,1);
 * literal-run copy handler 0x8001a418 (lbu (v1); sb (a1); a1++); back-reference match handler 0x8001a658;
 * NO jal; NO GTE/cop2; SINGLE caller (0x8003a4e4) => dedicated LEVEL.RAW decompressor. Control stream is BIG-ENDIAN.
 *
 * CONSEQUENCE: the floor at runtime 0x801bdc58 is the DECOMPRESSOR OUTPUT (valid fcn.80010000 payload), while
 * LEVEL.RAW[0xa81ac]=0x70d4001a is the COMPRESSED byte that loads at that address (decompression overwrote it).
 * So 0xa81ac is NOT a coordinate and NOT editable; CORRECTS the G22 "indexed-geometry stream" reading. NO safe
 * file-offset edit exists in compressed LEVEL.RAW; a floor edit needs decompress->edit->recompress (decode the
 * fcn.8001a1dc codec). NEXT (one BP): EXEC 0x8001a1dc -> read a0(src=LEVEL.RAW)/a1(dst=[gp+0x588])/size; confirm
 * [a1,a1+size) contains 0x801bdc58 (floor is decompressor output). Full detail:
 * src_re_geometry/geometry_g23_level_raw_floor_format.md.
 *
 * ============================================================================
 * G24 ADDENDUM (2026-06-15) — decompressor fcn.8001a1dc grammar (PARTIAL; LZSS/LZ77 + var-len codes)
 * --------------------------------------------------------------------------------------------------
 * Static decode of fcn.8001a1dc (0x8001a1dc..0x8001a8f8, ~456 instrs, single caller 0x8003a4e4):
 *   - prologue saves ALL GPRs; reads two BIG-ENDIAN header words word0=BE32[src+0], word1=BE32[src+4]
 *     (-> a2=dst+word0, a0=src+0xe+word1; BOTH computed then NEVER read = dead; purpose UNKNOWN); header is
 *     0xe bytes; v1 = src+0xe = bit/literal cursor; s1/dst = output.
 *   - BIT READER: MSB-first, one byte at a time from v1, guard-bit refill (~9 inlined reload sites).
 *   - MAIN LOOP 0x8001a658 = LZSS flag bit: 0 -> copy one inline literal byte (*a1++=*v1++); 1 -> match.
 *   - MATCH: variable-length length code via dispatch handlers (accumulate t0=t0*2+bit); escape at value 9
 *     (0x8001a4dc) -> long-literal Nx4 run (0x8001a3fc); long byte 0x8001a708 (byte==0 => STREAM TERMINATOR
 *     0x8001a804, else +8); 16-bit DISTANCE = (hi bits coded, byte-swapped) | (low byte inline from v1);
 *     back-ref source t6 = a1 - dist - 1; copy len bytes (odd-byte + 2/iter; RLE path when dist hi==0).
 *   - TERMINATION is bit/terminator-driven (NOT word0/a2); final t3 scratch-stack flush is a NO-OP here.
 * STRUCTURE CONFIRMED w/ PCs; EXACT length/distance code tables + word0/word1 meaning NOT byte-exact -> per the
 * task rule, NO offline decoder invented. NEXT (one BP, ground truth): EXEC 0x8001a1dc -> record hit count,
 * a0(=LEVEL.RAW 0x80115aac src), a1(=[gp+0x588] dst); at return dump decompressed output window. Floor
 * DECOMPRESSED offset = 0x801bdc58 - dst (DIFFERENT from compressed 0xa81ac). Full detail:
 * src_re_geometry/geometry_g24_level_raw_decompressor.md.
 *
 * ============================================================================
 * G25 ADDENDUM (2026-06-15) — LEVEL.RAW decompresses in a PER-CHUNK LOOP; floor is built POST-decompress
 * --------------------------------------------------------------------------------------------------------
 * Operator EXEC 0x8001a1dc trace: the decompressor is called MANY times (ra=0x8003a4ec, gp=0x80081d98 every hit)
 * -> it runs inside a PER-CHUNK LOOP in fcn.8003a318 (single static call site 0x8003a4e4, looped). This resolves
 * G24's "once vs per-block" -> PER-BLOCK. Loop structure (CONFIRMED disasm, fcn.8003a318 span 0x8003a318..0x8003c384):
 *   0x8003a4c8 lw fp,0x588(gp)        ; fp = decompressed-output cursor
 *   0x8003a4cc j 0x8003c2a4           ; -> loop head 0x8003c29c
 *   loop head 0x8003c29c: lbu s5[0..3]; if all == 0xff (word0 sentinel) -> FINALIZE 0x8003c2dc; else body 0x8003a4d4
 *   body 0x8003a4d4: jal 0x8001a1dc(a0=s5 compressed src, a1=fp dst); s4 = fp[0] = CHUNK SUBTYPE; s3 = fp;
 *                    big TYPE DISPATCH 0x8003a4ec..0x8003c250 consumes the decompressed chunk (s3) and builds a
 *                    runtime resource; per case fp += align4(word0) (e.g. 0x8003c13c); 10 fp-advance sites.
 *   tail 0x8003c250: v1 = BE32(s5[4..7]) + 0xe = word1 + 0xe; s5 += v1 (next compressed chunk); loop back.
 *   finalize 0x8003c2dc: [gp+0x4a0] = 0x801cc390 (high-heap TOP); [gp+0x588] = final fp; jal 0x80063508 x2; return.
 *
 * RESOLVES G24's "word0/word1 computed-then-dead": dead INSIDE the codec, LIVE in the caller -> word0 = per-chunk
 * DECOMPRESSED size (advances fp), word1 = per-chunk COMPRESSED size (advances s5), 0xe = chunk header length;
 * word0 == 0xffffffff = stream terminator. Matches the operator's per-chunk deltas (a0 += word1+0xe, a1 += word0).
 *
 * DECISIVE NEGATIVE (operator): the decompressor output cursor a1/fp tops at 0x8015fcbc; the floor 0x801bdc58 is
 * +0x5df9c ABOVE that -> the floor is NOT direct decompressor output. It sits in [final-fp 0x8015fcbc, high-top
 * 0x801cc390) = the upper high-heap buffer (consumed-compressed tail), 0xe738 below the top. Source-side bracket
 * for compressed offset 0xa81ac: the chunk with a0=0x801bd58f (next a0=0x801bf662) contains it (+0x6c9);
 * that chunk's decompressed output a1=0x80143438..0x80147500 (span 0x40c8).
 *
 * CORRECTED MODEL: the walkable floor fcn.80010000 payload at 0x801bdc58 is BUILT BY A POST-DECOMPRESSION STAGE
 * (a geometry-family subtype case in fcn.8003a318 writing into the high region, and/or a later converter that
 * reads the decompressed output) -- NOT by the raw decompressor. Exact writer/cursor = UNKNOWN. Candidate builders:
 * fcn.8003cc58 (x5, consumes s3+0xc), hot helpers 0x800628c0/0x800625fc (x10) / 0x80061a48 (x9), 0x80055db0,
 * finalize 0x80063508 (x2). NEXT (one decisive BP): WRITE watch 0x801bdc58 during load -> record writer PC/ra and
 * the source it copies (decompressed [.., 0x8015fcbc) vs leftover compressed [0x8015fcbc, 0x801cc690) vs computed);
 * secondary EXEC 0x8003a4ec to log per-chunk s4(subtype)/fp/s5. No patch/build. Full detail:
 * src_re_geometry/geometry_g25_level_raw_post_decompress_trace.md. Collision/pathing UNKNOWN (visual != collision).
 *
 * ============================================================================
 * G26 CORRECTION (2026-06-15) — 0x801bdc58 is COMPRESSED LEVEL.RAW SOURCE, NOT a floor render payload
 * --------------------------------------------------------------------------------------------------------
 * Operator ground truth RETRACTS the "walkable-floor payload at 0x801bdc58" premise that runs through the G18..G25
 * addenda above:
 *   (1) at "Press X to Continue", [0x801bdc58] = 70 D4 00 1A = 0x70d4001a = LEVEL.RAW[0xa81ac] EXACTLY (compressed).
 *   (2) WRITE watch 0x801bdc58 during LEVEL01 load = 0 HITS -> nothing ever writes there.
 * So 0x801bdc58 holds COMPRESSED LEVEL.RAW source bytes, unchanged across the whole load. It is NOT an fcn.80010000
 * payload: its "vertexCount" 0x70d4001a (~1.9 billion) is impossible (LEVEL.RAW is 0xb68e4 total) and the bytes are
 * high-entropy/compressed (G23). The G18 addendum line above ("<-- G18: walkable-floor payload lives here") and the
 * G18..G25 "floor at 0x801bdc58" framing are WRONG and SUPERSEDED.
 *
 * RE-AUDIT (disasm-grounded, why the old EXEC 0x800108b4 evidence misled): the a0-4 formula is CORRECT, not the bug.
 * In fcn.80010000 entry t7=[a0]=count; bgtz->main path (count>0), delay a0+=4, s5=a0=vertex base. In the count>0
 * main path 0x8001024c..0x800108xx, a0 is NEVER rewritten (only writes are entry a0+=4 and the count<=0 sub-path
 * 0x8001009c/ec/0x8001014c/0x80010174 < 0x8001024c); a0 is read as the vertex base for vtx=offset+a0; s5 IS reused
 * (lui s5,0x8008 @0x80010298). At gate 0x800108b4 (addi s3,s3,0x34): s3=GPU packet cursor (lw s3,(0x800823f4)),
 * s0=vertex cursor, a0=payload+4 -> payload=a0-4 is right FOR A GENUINE CALL. The G17 hits' a0-4=0x801bdc58 was
 * NEVER count-validated; [0x801bdc58]=0x70d4001a can't drive a clean 17-primitive emit -> those hits did not map to
 * a real floor payload (wrong context/timing/stale a0). FIX: validate [P] at capture time.
 *
 * WHAT STILL STANDS (LEVEL.RAW pipeline RE, independent of the floor): LEVEL.RAW loads compressed to 0x80115aac
 * (G22); 0x801bdc58 = LEVEL.RAW+0xa81ac (now PROVEN by the Press-X byte); fcn.8001a1dc decompresses in a per-chunk
 * loop in fcn.8003a318 with word0/word1 = per-chunk decompressed/compressed sizes (G24/G25). These characterize the
 * resource pipeline; they do NOT locate the floor render payload.
 *
 * STATUS: the walkable-floor/top-surface fcn.80010000 payload pointer is UNKNOWN. Re-find from the consumer side
 * at a confirmed floor view: PRIMARY EXEC 0x80010000 (a0=raw payload base; VALIDATE [a0]=plausible count; dump
 * first 0x40 bytes; record ra=caller); SECONDARY EXEC 0x800108b4 (payload=a0-4; cross-check count; read s3 packet
 * screen-XY / BP 0x80010718 SXY to confirm the prims land on the floor). Classify P: DAT-backed
 * (P-0x801607f8 in [0,0x51418)) vs LEVEL.RAW-decompressed (P < 0x8015fcbc output region) vs generated. No
 * patch/build. Full detail: src_re_geometry/geometry_g26_floor_payload_reaudit.md. Collision/pathing UNKNOWN.
 *
 * ============================================================================
 * G27 ADDENDUM (2026-06-15) — five count-validated fcn.80010000 payloads; Candidate A = strongest floor
 * --------------------------------------------------------------------------------------------------------
 * The operator ran the G26 consumer-side runbook (EXEC 0x80010000, a0 = RAW payload base, VALIDATE [a0]=count)
 * at the Candidate-B floor view and captured five payloads A-E. ALL FIVE pass the G26 acceptance test ([a0] =
 * claimed count EXACTLY: 83/48/58/36/25; pad==0 in 100% of verts; clean ffff ffff terminators; all N verts
 * referenced) and ALL FIVE are DAT-backed (a0 - DATbase 0x801607f8 in [0,0x51418)). Genuine payloads -- unlike
 * the retracted 0x801bdc58 (count 0x70d4001a, compressed). Decode via tools/analyze_g27_floor_candidates.py;
 * decoder validated by Candidate E reproducing the committed G18b 0x2d460 decode (25v, 202x107x194, flat 0.53,
 * 93 source-record refs).
 *
 *   cand  a0(payload)  DAToff   cnt  flat   Y-IQR  footprint    coordspace  refs  class
 *   A     0x801790c4   0x188cc   83  0.154  316    4502x4502    WORLD       1     FLOOR/TOP (STRONGEST)
 *   B     0x80199068   0x38870   48  0.260  234    1757x1680    WORLD       1     floor/top (adjacent tile)
 *   C     0x801994a8   0x38cb0   58  0.365  277    1706x2222    WORLD       1     floor/top (edge relief/ramp)
 *   D     0x80198d40   0x38548   36  0.568  422    1935x1874    MODEL       1     NOT floor (wall/struct-or-prop)
 *   E     0x8018dc58   0x2d460   25  0.530   67     202x194     MODEL       93    decor (CONFIRMED; = G18b)
 *
 * Split by STRUCTURE (not screen-visibility): A/B/C carry large positive WORLD coords in one shared Y~4400-5200
 * stratum -> co-planar baked terrain (floor family); D/E are centered on the local MODEL origin (+-100..+-950)
 * -> placed model objects (prop/decor; E instanced x93). A is the flattest (0.154, beats the whole prior static
 * floor shortlist; G17 best e135=0.19), tightest-Y (316), widest (4502x4502), world-space, unique, count 83 --
 * the STRONGEST floor/top-surface candidate -- and DAT-backed (off 0x188cc) => DIRECTLY EDITABLE, the property
 * the retracted heap floor 0x801bdc58 lacked. D rejected as floor (flat 0.568, big Y relief, model-space).
 *
 * IMPLICATION FOR THE "next resource"/heap-floor narrative above: the G17/G18 "walkable floor is NOT a LEVEL.DAT
 * payload" inference rested ENTIRELY on the retracted 0x801bdc58 (G26). The count-validated floor-view emit DOES
 * surface DAT-backed, flat, world-space floor-shaped payloads (A/B/C) -> that inference is DOWNGRADED. UNKNOWN
 * (not claimed): whether A is the WALKABLE surface vs a co-planar visual chunk, and whether any LEVEL.RAW-
 * decompressed/generated payload also feeds the view (A-E is the captured set, not proven exhaustive). NOTE:
 * 0x8018dc58 (Candidate E, DAT 0x2d460) is a VALID DAT payload; 0x801bdc58 is INVALID compressed LEVEL.RAW source
 * -- one hex digit apart; do not conflate.
 *
 * NEXT (one read-only BP, no patch/build): EXEC 0x800108b4, keep a0==0x801790c8 (Candidate A vertex base), read
 * the s3 GPU packet screen-XY (or EXEC 0x80010718 SXY) -> confirm A's survivors land in the lower-center walkable
 * band before any edit (G16: emit-in-frame != floor). Contingent same-size edit spec ready (A v16 y @DAT 0x18992
 * 89 13 -> 89 17, +1024, single byte; revert 89 13) but NOT built. Full detail:
 * src_re_geometry/geometry_g27_count_validated_floor_candidates.md. Collision/pathing UNKNOWN (visual != collision).
 *
 * ============================================================================
 * G28 ADDENDUM (2026-06-15) — Candidate A runtime READ + PROJECTION confirmation; visual test = VISIBLE TERRAIN DEFORM
 * --------------------------------------------------------------------------------------------------------
 * The operator ran the G27 §5 / G26 SECONDARY runbook in the Candidate-B floor/top-surface view and CONFIRMED
 * Candidate A reaches the render/projection path:
 *   - READ watch 0x801790c8 (Candidate A vertex base) -> HIT REPEATEDLY, with a0=0x801790c8, ra=0x800206a0,
 *     payload base = a0-4 = 0x801790c4, count at payload base = 83 (matches G27).
 *   - EXEC 0x80010718 (per-primitive site, right after mfc2 SXY0/1/2) HIT while Candidate A active:
 *       prim1: a0=0x801790c8 ra=0x800206a0  SXY0=0x007A0164 SXY1=0x00730182 SXY2=0x007B0180
 *       prim2: a0=0x801790c8 ra=0x800206a0  SXY0=0x007F01A8 SXY1=0x007701CF SXY2=0x008501F1
 *     Unpacking (Y<<16)|X (signed halves, G16): Y clusters ~115-133 (central/lower-central band) -> plausible
 *     lower/central floor projection; X ~356-497 recorded raw (exact horizontal viewport mapping = TODO, G16).
 *
 * PRE-TEST CLASSIFICATION: Candidate A (0x801790c4 / DAT 0x188cc / count 83) =
 *   VALID DAT-BACKED PAYLOAD / RUNTIME READ CONFIRMED / PROJECTION PATH CONFIRMED /
 *   LIKELY VISUAL FLOOR/TOP-SURFACE / TANGIBILITY UNKNOWN.
 *
 * KEEP SEPARATE: 0x801790c4 (Candidate A, valid DAT payload, this addendum) vs 0x801bdc58 (compressed LEVEL.RAW
 * source, RETRACTED G26, never written/never a payload) -- one hex digit apart, entirely different. The G26
 * retraction stands; the LEVEL.RAW pipeline RE (G22-G25) stands as resource characterization.
 *
 * BUILT + OPERATOR-TESTED (2026-06-15): the guarded same-size reversible edit tools/patch_g28_candidate_a_floor_y_test.py
 *   LEVEL01/LEVEL.DAT @ 0x18992 (Candidate A vertex 16 y; runtime base 0x80179188, y at 0x8017918a):
 *   89 13 (0x1389=5001) -> 89 17 (0x1789=6025), delta +1024, single byte 0x18993 13->17; revert 89 13. Same-size
 *   (0x51418) only; never in place; touches no collision/pathing files. Built via the shared rebuild wrapper
 *   (tools/rebuild_with_patched_dat.py) -> ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue (patched DAT sha1 a1cf8d8e...,
 *   embedded verified LBA 2906, staged workspace restored to pristine; artifacts gitignored/not committed).
 *
 * VISUAL TEST RESULT (operator, ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue): boots YES; LEVEL01 loads YES; the tested
 *   floor/terrain area VISIBLY DEFORMS (caves inward; shifts slightly with viewing angle) in the lower/central
 *   region matching Candidate A's projected area; Flik and other objects still render; collision/pathing does NOT
 *   align with the visual deformation.
 * POST-TEST CLASSIFICATION: Candidate A = CONFIRMED DAT-BACKED VISUAL TERRAIN/FLOOR RENDER PAYLOAD (the DAT+0x18992
 *   edit affects visible terrain geometry; A is NOT decor/grass/prop; A is part of the visible floor/top-surface
 *   render mesh in the tested area). LIKELY A belongs to the visible floor/top-surface mesh family of the
 *   Candidate-B view. UNKNOWN: the collision/pathing source for this surface; whether A has collision/tangibility
 *   data elsewhere. EXPLICIT: visual terrain payload != collision/pathing source -- the tested deform did not
 *   alter/align with collision, so collision/pathing is SEPARATE or sourced elsewhere (no claim collision moved;
 *   no tangibility claim). Full detail: src_re_geometry/geometry_g28_candidate_a_runtime_confirmation.md.
 *
 * NEXT (recommended G29): collision/pathing SOURCE discovery for this CONFIRMED visual floor terrain. Do NOT assume
 *   it is in Candidate A, LEVEL.DAT, or LEVEL.RAW without new evidence. Use runtime collision probes /
 *   movement-height (floor-contact) reads / floor-contact state, not the visual render path alone.
 *
 * ============================================================================
 * G29 ADDENDUM (2026-06-15) — collision/floor source is NOT in these render buffers; runtime-first plan
 * --------------------------------------------------------------------------------------------------------
 * G28 proved Candidate A (DAT 0x188cc / runtime 0x801790c4, count 83) is a VISUAL floor payload whose
 * deform did NOT move collision. So NONE of the buffers catalogued here (PASS-1 output array 0x801b1c10,
 * source/payload bands inside the DAT, the reserved gap) is the floor COLLISION source — they are render
 * geometry. The collision/floor-height source is UNKNOWN and is approached from the PLAYER-Y side, not the
 * render buffers:
 *   - player Y = 0x800a6504 (X 0x800a6500 / Z 0x800a6508); floor contact resolves into Y.
 *   - Pass 1: WRITE watch 0x800a6504 -> the writer PC = floor/movement integrator (LIKELY fcn.8005b134).
 *   - Pass 2: that writer reads a floor-height value `S`; classify S vs the bands mapped in this file —
 *       DAT image [0x801607f8,0x801b1c10) (but NOT Candidate A's vertex band ~0x80179188),
 *       PASS-1 output [0x801b1c10,0x801b5890), reserved gap [..0x801b6a10), heap/"next resource"
 *       [0x801b6a10..), or LEVEL.RAW-decompressed region (<0x8015fcbc, G25). Record which band holds S.
 *   - Reminder: 0x801bdc58 (in the "next resource" region noted above) is COMPRESSED LEVEL.RAW source
 *       (G26, never written) — NOT a floor buffer; do not use it as a collision pointer.
 * Full plan + runbook: src_re_geometry/geometry_g29_collision_source_plan.md. No patch/build. Visual != collision.
 *
 * ============================================================================
 * G29 PASS 1 ADDENDUM (2026-06-15) — player-Y writer found; floor source S lives in a gp-scratch list
 * --------------------------------------------------------------------------------------------------------
 * Pass 1 WRITE watch 0x800a6504 ran (pristine). Writer = FUNC_3633C @0x8003633c (movement+collision integrator;
 * s7=player base 0x800a6500, s5=velocity 0x800a652c, contact flags 0x800a6582; caller 0x800495c8 RA 0x800495d0).
 * DuckStation reports PC=store+4. The floor/contact-corrected Y is written at 0x80036cec (v1=[sp+0x1c], the
 * collision-RESOLVED position from helper 0x800345cc); the 0x80036380/0x80036d54 hits are a +-0xc80 probe bias.
 * NOT fcn.8005b134 (superseded/pending; see geometry_collision_consumers.c).
 *
 * IMPLICATION FOR THIS BUFFER MAP: the collision helpers 0x800345cc/0x80035280 iterate a PER-FRAME collision-
 * candidate list whose COUNT is at [gp+0x57c] = 0x80082314 (gp=0x80081d98 rt) -- a gp-relative SCRATCH region just
 * below the parser globals (0x800822f0..0x80082508), NOT any of the render buffers catalogued in this file. The
 * floor-height source S is an element of that candidate list (Pass 2 will read its base + S's address, then
 * classify S vs the bands mapped here: DAT image [0x801607f8,0x801b1c10) but NOT the Cand-A vertex band
 * ~0x80179188 / PASS-1 output [0x801b1c10,0x801b5890) / reserved gap [..0x801b6a10) / heap "next resource"
 * [0x801b6a10..) / LEVEL.RAW-decompressed <0x8015fcbc). No band assigned yet -- UNKNOWN until Pass 2. No patch/build.
 *
 * G29 PASS 2 (2026-06-15): resolved player position is built in a STACK working buffer (FUNC_3633C sp+0x18, e.g.
 * 0x801FFE18), NOT in any buffer mapped in this file. The accumulate `pos += delta` (helper 0x800345cc @0x80035ed8)
 * and the seed-copy (FUNC_3633C @0x80036bdc) both write that stack slot; the floor-height value originates in the
 * per-frame collision-candidate list (counts [gp+0x57c]=0x80082314, [gp+0x5cc]=0x80082364; gp-scratch, below the
 * parser globals), produced by sweep helper 0x80035f24. Its BACKING REGION is still UNKNOWN -> the band classification
 * (DAT / LEVEL.RAW-decompressed / heap / generated) above remains TODO, to be resolved by EXEC 0x80035f24 next.
 * Note: the caught invocation ran on a stack position vector (s7=0x801FFEA8), not the player global -- no claim that
 * stack address is the player. No patch/build.
 *
 * G29 candidate-record read/compare evidence (2026-06-15): the collision-candidate records this integrator walks
 * live at 0x800F7xxx -- a runtime/heap/BSS region ABOVE the exe text end (~0x80082800) and BELOW LEVEL.DAT
 * (0x801607f8) / LEVEL.RAW (0x80115aac); none of the buffers mapped in this file. Backing source UNKNOWN (NOT
 * DAT/RAW/decompressed). FUNC_3633C's range-overlap loop (0x800369a0..0x80036b7c) copies matched candidates into an
 * output list at 0x80090868 (stride 0xc, count [gp+0x5cc]=0x80082364). A captured candidate field [t1-0x08] (== the
 * +4 word of a 0xc-stride sub-record) is LIKELY a compare/selection scalar -- semantic UNKNOWN, NOT confirmed floor
 * height. Detail: geometry_g29_collision_source_plan.md sec 2.7. No patch/build.
 * ============================================================================ */

#include "../src_re/re_types.h"

/* ---- CANDIDATE runtime-buffer descriptors (local to G3; NOT promoted to re_types.h) ---- */

/* (1) PASS-1 OUTPUT BUFFER: array of ParserOutputRecord20 (see dat_geometry_records.c).
 *     base = DATbase + arg2 (CONFIRMED rel.); LEVEL01 LIKELY 0x801b1c10; count = pass1 entries (484).
 *     Only pass-1 writes here; pass-3 does not. Role (render/collision) UNKNOWN -> G4/G5. */

/* (2) SOURCE-RECORD band [DATbase+0x45f0, DATbase+0x8bd8): the relocated ParserSrcRec18/20 records
 *     that pass-1 transforms and pass-3 relocates-only. Lives inside the DAT image. */

/* (3) PAYLOAD band [DATbase+0x8bd8, DATbase+0x4f32c]: targets of source +0x14/+0x1c. Role UNKNOWN.
 *     624 distinct targets; contents not decoded (G3 catalogs relationship only, assigns no role). */

/* (4) Parser-stored runtime pointers (resident globals; CONFIRMED they hold DATbase+fileoffset): */
typedef struct ParserRuntimePtrs_G3 {
    /* G_DAT_BASE_PTR     0x80082498 = DATbase (heap cursor at load time)        */
    /* G_TRAIL_BLOCK_PTR  0x800824ac = DATbase + 0x1504   (trailing block)       */
    /* G_PASS2_BASE_PTR   0x80082338 = DATbase + 0x3ae8   (pass-2 base, empty)   */
    /* G_PASS3_BASE_PTR   0x80082508 = DATbase + 0x3aec   (pass-3 base)          */
    /* G_DAT_ENTRY_COUNTER 0x800822f0 = pass1+pass3 entry count (return = <<5)    */
    /* gp+0x604 (0x8008239c) = epilogue out_end - tail (when tail != -1)         */
    int32_t _doc_only;
} ParserRuntimePtrs_G3;

/* There is NO dedicated global holding the pass-1 output base; it is recomputed as DATbase+arg2.
 * The heap/resource cursor is the caller's stack local [sp+0x98], not a named global. */

/*
 * G3 OPEN ITEMS handed to G4/G5:
 *  [ ] Concrete DATbase: trace the [sp+0x98] cursor's initial value up the caller chain to make the
 *      absolute addresses CONFIRMED rather than LIKELY (optional; relationships already hold).
 *  [ ] Confirm arg2 is exact file size vs sector-padded (would shift output base) — needs fcn.80046330.
 *  [ ] Role of the 0x1180 reserved gap: is pass-3 output written there by a later consumer, or slack?
 *  [ ] Who reads the PASS-1 output buffer (matrix path)?  -> G4/G5.
 *  [ ] Who reads the PASS-3 relocated source records (direct path)?  -> G4/G5 (keep separate).
 *  [ ] Payload-band contents/roles -> deferred (no role assignment in G3).
 *  [ ] Do NOT promote to re_types.h until a field is confirmed by producer AND consumer.
 */

/* RCA a4 (2026-07-09): SUPERSEDED for build purposes — 0x80046330 is byte-matched in the
   shipping build as asm/hand_written/80046330_universal_file_loader.s (config/segments.yml `attempted`;
   validate_build.py SHA-1 PASS). This src_re file is documentation-grade pseudocode,
   retained for its analysis/comments; it is NOT the build unit. */
/* src_re/file_loader_80046330.c -- ABL generic "load file by name -> RAM" loader.
 *
 * RE'd 2026-06-26 while scoping Tier-3 render disc-delivery (see
 * ObsidianVault/Findings/Finding - Tier-3 render disc-delivery.md). Identities are VERIFIED by
 * disassembly on the running game (DuckStation external debugger); bodies are partial/behavioural.
 *
 * Resource load chain (ObsidianVault/Systems/Systems.md):
 *   FUNC_8003CF2C (resource dispatcher)
 *     -> FUNC_80046330 (THIS: generic file loader, name -> dest)
 *        -> FUNC_80045FC4 (file lookup: CdSearchFile by name -> LBA + size)
 *     -> FUNC_8001CDC0 (LEVEL.DAT parse)  | FUNC_8003A318 (LEVEL.RAW load+decompress)
 *
 * KEY for modding: FUNC_80046330 takes a FILENAME STRING and a DEST address. It is the routine to
 * reuse to pull a NEW custom file off the disc into RAM (e.g. the Tier-3 render cave), since neither
 * LEVEL.DAT nor LEVEL.RAW has spare on-disc room to append to (both fill their LBA slots exactly).
 */

/* ---- libcd / helpers referenced (addresses, not re-implemented) -------------------------------- */
/* 0x8006f690  CdSearchFile(CdlFILE *out, const char *name) -> CdlFILE* (0 = not found)              */
/* 0x8006d8e8  libcd command send (CdControlB-class; called with cmd in a0)                          */
/* 0x8005f74c  strcpy/strcat-class (dst=a0, src=a1)   0x8005f76c  buffer init (a0)                   */
/* 0x80045E00  xa_open(id) -- the music path's CdSearchFile filler (same lookup family)              */

/* FUNC_80045FC4 -- resolve a filename to its CdlFILE (first sector + size) via CdSearchFile.
 * a0 = name (already uppercased by the caller), a1 = out CdlFILE*. Retries the search until found
 * (`beq v0,zero, retry` at 0x8004600c around CdSearchFile @0x8006f690). The file's LBA/size live in
 * the returned CdlFILE (read at sp+0x14 = entry.pos/.size). Returns status. */
extern int FUNC_80045FC4(const char *name, void *out_cdlfile);   /* 0x80045fc4 */

/* FUNC_80046330 -- load an entire named file off the CD into RAM.
 *   a0 = filename string (case-insensitive; the loader UPPERCASES a-z in place -- ISO9660 norm:
 *        @0x8004639c  `v0 = c - 'a'; if ((unsigned)v0 < 26) c += -32;`  i.e. tolower->TOUPPER).
 *   a1 = destination RAM address (fp in the body).
 * It copies the name into a local buffer (strcpy 0x8005f74c into sp+0x10), uppercases it, then
 * FUNC_80045FC4 -> CdSearchFile resolves name -> {LBA,size}, and the libcd block (0x80062xxx calls:
 * 0x80062560/0x800625fc/0x80062a4c/0x80062c70/0x80062ec8/0x800651d0...) reads `size` bytes (the WHOLE
 * file, taken from the directory entry -- NOT a header field) starting at LBA into `dest`.
 * NO decompression here -- callers decompress (FUNC_8003A318 wraps this for LEVEL.RAW). So a RAW
 * (uncompressed) custom file loads verbatim. Return at 0x800464e4 reads gp+0x6ec (status/size). */
extern int FUNC_80046330(const char *name, void *dest);          /* 0x80046330 */

/* FUNC_8003A318 -- LEVEL.RAW load orchestrator (high-heap). Verified caller of FUNC_80046330:
 *   @0x8003a360  v0 = size_query(a0)        (jal 0x8004589c)
 *   @0x8003a37c  dest = 0x801D0000 - 0x3C70 - ((v0+3) & 0x00FFFFFC)   (top-down high-heap alloc)
 *   @0x8003a388  jal FUNC_80046330(a0=resource, a1=dest)             (raw file -> high heap)
 *   then FUNC_8001A1DC decompresses the loaded RNC/PROPACK chunks in-place per-chunk.
 * Shows the idiom: pick a high-heap dest, call the by-name loader, (optionally) decompress. */

/* ---- Filename format (traced live 2026-06-26) -------------------------------------------------
 * The `name` arg is a FULL RELATIVE path "dir\file.ext": lowercase, BACKSLASH separator, no leading
 * slash, no ";1" version (observed: "fmv\fmv.bin", "sfx\global.vh", "level00\level3.raw"). The loader
 * uppercases it for CdSearchFile. (This file is pure RE; the Tier-3 mod that reuses this loader lives in
 * mod/tier3_loader.asm + mod/caves/tier3_collision.c -- see Finding - Tier-3 render disc-delivery.) */

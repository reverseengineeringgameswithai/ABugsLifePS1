/* audio_music.h — XA streamed-music engine types/constants for A Bug's Life
 * (SCUS-94288) hand-decompilation.  Companion to re_types.h.
 *
 * SCOPE: only structs/fields/constants SUPPORTED BY NOTES (static disasm +
 *        in-game confirmation).  Confidence markers: CONFIRMED / LIKELY / UNKNOWN.
 * Source of truth: ObsidianVault/Core - Runtime Audio Path.md (GAP-0031 section),
 *        ObsidianVault/Findings/Finding - XA streamed music replacement.md.
 *
 * The runtime uses PsyQ libcd. We reconstruct against the real libcd ABI: the
 * music engine drives the CD into XA-ADPCM streaming via CdControlB() command
 * bytes, exactly as observed at 0x80046a6c / 0x80046aa0.
 */
#ifndef ABL_AUDIO_MUSIC_H
#define ABL_AUDIO_MUSIC_H

#include <stdint.h>

/* --- PsyQ libcd shims (real ABI; only what the music path touches) --------- */
typedef struct { uint8_t minute, second, sector, track; } CdlLOC;   /* BCD position */
typedef struct { uint8_t file, chan; }                    CdlFILTER;/* XA file/channel */

/* libcd command bytes used by the music engine (CONFIRMED at the call sites). */
#define CdlSetloc     0x02  /* seek target (CdlLOC) */
#define CdlPause      0x09  /* stop streaming */
#define CdlMute       0x0b
#define CdlDemute     0x0c  /* observed at music start */
#define CdlSetfilter  0x0d  /* XA file/channel select — 0x80046a6c */
#define CdlSetmode    0x0e  /* observed param 0xe8 */
#define CdlReadS      0x1b  /* streamed read (XA) — 0x80046aa0 */

/* CdlSetmode param observed = 0xe8 = Speed(0x80) | RT/ADPCM(0x40) |
 * SectorSize(0x20) | SubheaderFilter(0x08).  CONFIRMED. */
#define CD_MODE_XA_STREAM 0xe8

extern void  CdControlB(uint8_t com, const uint8_t *param, uint8_t *result); /* libcd */
extern CdlLOC *CdIntToPos(int i, CdlLOC *p);                                  /* libcd */
extern int    CdPosToInt(const CdlLOC *p);                                    /* libcd */
extern int    CdGetToc(CdlLOC *toc);
/* CdGetlocL-style position read is wrapped by the game at 0x8006dcb0. */

/* ---------------------------------------------------------------------------
 * XA stream descriptor table.  CONFIRMED.
 *   Base RAM 0x800772c8 (EXE file off 0x67ac8), 5 records x 12 bytes, one per
 *   BUGXASTR/AUDIOn.XA (record N -> AUDIO(N+1)).  `name` points at the
 *   "\BUGXASTR\AUDIOn.XA;1" string (e.g. 0x8001b140 for AUDIO1).  `start` and
 *   `size` are zero on disc and filled at runtime by the file open path
 *   (FUNC_80045e00 -> CdSearchFile), where `start` is the file's first sector.
 * --------------------------------------------------------------------------- */
typedef struct XaStreamDesc {
    const char *name;   /* +0x00 CONFIRMED -> "\BUGXASTR\AUDIOn.XA;1"           */
    CdlLOC      start;  /* +0x04 CONFIRMED file start position (runtime, BCD)    */
    uint32_t    size;   /* +0x08 LIKELY    file size in sectors (runtime)        */
} XaStreamDesc;         /* sizeof = 0x0c CONFIRMED */

#define G_XA_STREAM_TABLE  0x800772c8u /* CONFIRMED XaStreamDesc[5] */

/* Music control globals. gp = 0x80081d98 (see re_types.h). */
#define G_MUSIC_ID         0x8008245cu /* CONFIRMED current packed music id sink */
#define G_MUSIC_AREA_CTR   0x8008243cu /* CONFIRMED area counter; switch 0x8001b3c4 */
#define G_MUSIC_SWITCH_JT  0x8001b3c4u /* CONFIRMED area -> music_id jump table    */
#define G_MUSIC_TRACK_ID   0x80082420u /* CONFIRMED [gp+0x420] active stream record idx (a0>>3) */
#define G_MUSIC_LOC_BUF    0x80082458u /* LIKELY    [gp+0x458] last CdGetlocL buffer */
#define G_MUSIC_END_MARK   0x80081ff0u /* LIKELY    [gp+0x670] track end marker (poll compare) */
#define G_MUSIC_SPECIAL    0x8008225cu /* CONFIRMED !=0 -> cutscene/special music override (a0=0x15) */

/* Packed music id encoding (CONFIRMED): file = (id>>3), channel = (id & 7);
 * disc file = AUDIO(file+1).  Examples (in-game): id 0x00 -> AUDIO1 ch0
 * (LEVEL01 sustained gameplay theme, CONFIRMED in-game); id 0x12 -> AUDIO3 ch2
 * (a ~12s LEVEL01 LOAD cue, NOT the gameplay loop). */
#define MUSIC_FILE(id)     ((id) >> 3)
#define MUSIC_CHAN(id)     ((id) & 7)

#endif /* ABL_AUDIO_MUSIC_H */

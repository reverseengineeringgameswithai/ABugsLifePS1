---
kind: function
id: FUNC_8004699C
aliases:
- FUNC_8004699C
- 2147772828
- '0x8004699c'
- music_start
address: '0x8004699c'
name: music_start
status: byte_matched
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
- src_re/music_8004699c.c
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- src_re/music_8004699c.c
- src/main/8004699c_music_start.c
patch_policy: unknown
---

# FUNC_8004699C - music start

## Purpose

Generated from C source coverage. The original-game behavior should be refined manually with call/read/write links.

## Known behavior

See the exact source excerpt below. Preserve `UNKNOWN`, `LIKELY`, and `TODO` labels from the source comments.

## Address / identity

- Address: `0x8004699C`
- Name: `music_start`
- Source path: `src_re/music_8004699c.c`

## C source excerpt

Source: `src_re/music_8004699c.c`

```c
/* ============================================================================
 * music_8004699c.c — XA streamed-music engine [DECOMPILED — runtime CONFIRMED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESSES : FUNC_8004699c  music_start(packed_id)   — selector + start
 *                      0x80046a6c     CdlSetfilter call site (file=1, chan=id&7)
 *                      0x80046aa0     CdlReadS call site (XA streaming begins)
 *                      FUNC_80046828  music_poll()             — per-frame loop poll
 *                      0x80046ac0     music_play_once(id)      — public wrapper
 *                      0x80046ae8     music_play_looping(id)   — public wrapper
 *                      FUNC_80045e00  xa_open(id)              — CdSearchFile fill
 *                        (table read at 0x80045e90: lw a1,0x72c8(at), at=0x80077000)
 *                      FUNC_8004fa40  music_engine_reset()     — area ctr -> 0
 *                      0x8005bc34     level_music_start()       — passes packed id
 * CONFIDENCE         : CONFIRMED — packed-id encoding (file=id>>3, chan=id&7),
 *                      the CdlSetfilter{file=1,chan} + CdIntToPos + CdlReadS +
 *                      CdlSetmode(0xe8) + CdlDemute/CdlPause sequence, the 5-entry
 *                      XaStreamDesc table @0x800772c8, AND the in-game fact that
 *                      LEVEL01's sustained theme = AUDIO1 ch0 (packed id 0x00).
 *                      LIKELY — the exact poll end-compare operands and the
 *                      gp-relative scratch offsets (modelled from the trace).
 * SOURCE NOTES       : ObsidianVault/Core - Runtime Audio Path.md (GAP-0031),
 *                      Finding - XA streamed music replacement.md, live execTrace
 *                      (pc 0x8004699c a0; pc 0x80046a78 s0=chan), r2 (MIPS LE,
 *                      gp=0x80081d98).
 * KNOWN CALLERS      : 0x8005bc34 level_music_start (a0 = music_id-1 from G_MUSIC_ID);
 *                      music_engine_reset 0x8004fa40 (boot init 0x8005f730).
 * KNOWN CALLEES      : libcd CdControlB / CdIntToPos / CdGetlocL-wrapper 0x8006dcb0;
 *                      CdSearchFile (via xa_open FUNC_80045e00).
 * NOTE ON LOOPING    : looping is SOFTWARE — music_poll() re-issues the whole
 *                      start sequence at the saved stream start when the read
 *                      reaches the track end.  It is NOT the XA EOF subheader bit.
 *                      => any byte-for-byte (size-preserving) channel payload swap
 *                         keeps the loop identical (see tools/xa_splice.c).
 * ============================================================================ */

#include "re_types.h"
#include "audio_music.h"

#define LBU(p)  (*(uint8_t  *)(p))
#define LW(p)   (*(int32_t  *)(p))
#define SB(p,v) (*(uint8_t  *)(p) = (uint8_t)(v))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))

static XaStreamDesc *const xa_table = (XaStreamDesc *)G_XA_STREAM_TABLE;

/* FUNC_80045e00 — resolve AUDIOn.XA on disc (fills desc.start/size).  CONFIRMED
 * the table read (0x80045e90); CdSearchFile body summarized. Returns desc. */
XaStreamDesc *xa_open(int stream_idx) /* stream_idx = packed_id >> 3 */
{
    XaStreamDesc *desc = &xa_table[stream_idx];
    /* CdSearchFile(&entry, desc->name) -> fills desc->start (file 1st sector)
     * and desc->size (sectors).  Done once; cached in the table thereafter. */
    /* ... CdSearchFile elided (libcd) ... */
    return desc;
}

/* FUNC_8004699c — start streaming a packed music id.
 *   packed_id: file = packed_id>>3 (-> AUDIO(file+1)), channel = packed_id & 7.
 * Observed live: LEVEL01 gameplay -> packed_id 0x00 (AUDIO1, ch0). */
void music_start(int packed_id)
{
    int          stream_idx = MUSIC_FILE(packed_id);   /* a0 >> 3            */
    int          channel    = MUSIC_CHAN(packed_id);   /* a0 & 7            */
    XaStreamDesc *desc;
    CdlFILTER    filter;
    CdlLOC       loc;
    uint8_t      mode = CD_MODE_XA_STREAM;             /* 0xe8              */

    SW(G_MUSIC_TRACK_ID, stream_idx);                  /* [gp+0x420] = idx  */
    desc = xa_open(stream_idx);                        /* resolve AUDIOn.XA */

    /* 0x80046a6c: build CdlFILTER{file=1, chan} and select it.
     * NB: the XA-subheader "file" field is hard-coded 1; the AUDIOn selection
     * is the disc *file* (via desc), the channel is the variable. */
    filter.file = 1;                                   /* sb 1,  0x40(sp)   */
    filter.chan = (uint8_t)channel;                    /* sb s0, 0x41(sp)   */
    CdControlB(CdlSetfilter, (uint8_t *)&filter, 0);   /* com 0x0d          */

    /* seek to the stream start and begin XA streaming */
    loc = desc->start;                                 /* saved start LOC   */
    CdControlB(CdlSetmode, &mode, 0);                  /* com 0x0e, 0xe8    */
    CdControlB(CdlSetloc,  (uint8_t *)&loc, 0);        /* com 0x02          */
    CdControlB(CdlReadS,   0, 0);                      /* 0x80046aa0 com 0x1b */
    CdControlB(CdlDemute,  0, 0);                      /* com 0x0c          */
}

/* music_poll — FUNC_80046828, called per frame while music is active.
 * Reads the current CD position (CdGetlocL wrapper 0x8006dcb0 -> G_MUSIC_LOC_BUF)
 * and, when the stream has reached the track end, RE-ISSUES the start sequence at
 * the saved start position -> seamless software loop.  The end test is modelled
 * from the trace (compare current sector vs the stored end marker); operands
 * marked LIKELY. */
void music_poll(void)
{
    uint8_t *loc = (uint8_t *)G_MUSIC_LOC_BUF;        /* [gp+0x458] filled by wrapper */
    int      cur_sector;
    int      end_sector;

    /* CdGetlocL wrapper writes the 8-byte location header to G_MUSIC_LOC_BUF;
     * +0xc/+0xe hold the running sector/position fields the poll compares. */
    /* ... CdGetlocL(0x8006dcb0) -> loc ... */
    cur_sector = LW(G_MUSIC_LOC_BUF + 0x0c);          /* LIKELY running position */
    end_sector = LW(G_MUSIC_END_MARK);                /* [gp+0x670] LIKELY end   */

    if (cur_sector >= end_sector) {                   /* reached track end -> loop */
        int           idx  = LW(G_MUSIC_TRACK_ID);
        XaStreamDesc *desc = &xa_table[idx];
        CdlFILTER     filter;
        CdlLOC        loc2 = desc->start;             /* saved start (+0x72cc)   */
        uint8_t       mode = CD_MODE_XA_STREAM;

        filter.file = 1;
        filter.chan = (uint8_t)MUSIC_CHAN(LBU(G_MUSIC_ID)); /* same channel */
        CdControlB(CdlSetfilter, (uint8_t *)&filter, 0);
        CdControlB(CdlSetmode,  &mode, 0);
        CdControlB(CdlSetloc,   (uint8_t *)&loc2, 0);
        CdControlB(CdlReadS,    0, 0);                /* restart from start -> loop */
    }
}

/* Public wrappers (resident EXE). */
void music_play_once(int packed_id)    /* 0x80046ac0 */
{
    SB(G_MUSIC_ID, packed_id);
    music_start(packed_id);
}

void music_play_looping(int packed_id) /* 0x80046ae8 */
{
    SB(G_MUSIC_ID, packed_id);
    music_start(packed_id);            /* loop handled by music_poll() per frame */
}

/* FUNC_8004fa40 — reset at boot init (0x8005f730). Clears the area counter so the
 * area->music_id switch (0x8001b3c4) defaults to case 0 (music_id 1 -> a0=0 ->
 * AUDIO1 ch0).  CONFIRMED: this is why LEVEL01's default theme is AUDIO1 ch0. */
void music_engine_reset(void)
{
    SW(G_MUSIC_AREA_CTR, 0);
    SW(G_MUSIC_ID, 0);
}

/* level_music_start — 0x8005bc34 (summarized): chooses the packed id for the
 * loaded area and starts it.  a0 = G_MUSIC_ID - 1 in the resident path; the
 * per-area value arrives via the area switch (0x8001b3c4) or a per-level seed.
 * A gated override uses packed id 0x15 (AUDIO3 ch5) when G_MUSIC_SPECIAL != 0. */
void level_music_start(void)
{
    int packed_id = LW(G_MUSIC_ID) - 1;
    if (LW(G_MUSIC_SPECIAL) != 0)
        packed_id = 0x15;              /* AUDIO3 ch5 cutscene/special */
    music_play_looping(packed_id);
}
```

## Evidence

- Source: `src_re/music_8004699c.c`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

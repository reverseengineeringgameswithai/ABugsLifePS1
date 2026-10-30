/* ============================================================================
 * fmv_movie_dispatch_800b6250.c  — FMV movie-id selection dispatch [PHASE 4 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : 0x800B6250 .. ~0x800B658C, INSIDE the FMV.BIN overlay (loaded to
 *                    Region-B base 0x800B5788, file offset 0xAC8). This is NOT part of
 *                    the resident EXE — it exists only while FMV.BIN is the resident
 *                    Region-B module. CONFIRMED as the FMV.BIN entry point: it is the
 *                    target of fmv_bin_load's final call (see fmv_player_streaming.c),
 *                    called with a0 = movie_id, unchanged from the trigger site.
 * CONFIDENCE        : CONFIRMED (bounds check, jr-table, case bodies, tail call target,
 *                    the DEFAULT handler). Documentation-grade C, like the contact_*
 *                    files; NOT a build unit — FMV.BIN has never been through the
 *                    function-boundary-recovery pipeline the resident EXE overlays get
 *                    (analysis/phase4_e15_fmv_frontier.json), so exact case-body extents
 *                    beyond what's modelled here are unverified.
 * KNOWN CALLERS     : fmv_bin_load (0x8003E7C0, resident) — see fmv_player_streaming.c
 *                    for the FULL trigger chain. A whole-executable Phase-4 C census
 *                    supersedes the old 3-site claim: there are 9 direct resident
 *                    fmv_bin_load calls and zero overlay calls.
 * KNOWN CALLEE      : FUNC_800B6D68 (fmv_playback_start, undecompiled — the actual
 *                    MDEC/CD-streaming pump; item 2's remaining residual).
 *
 * THE TABLE BELOW IS THE COMPLETE, VERIFIED movie_id -> (STR path, frame count) MAPPING.
 * 47 slots: 3 boot/frontend clips (0-2) + 7 unused/reserved (3-9, all share the DEFAULT
 * handler below) + 37 real per-level/ending clips (10-46). This SUPERSEDES an earlier
 * "11 levels" reading of FMV.BIN's own in-file 25-entry manifest header, which is STALE
 * relative to what this dispatch table actually references — the true campaign coverage
 * is 15 levels (matching all 15 F01-F15 campaign stages) plus 3 ALT endings, an INTRO,
 * and a LOSE (game-over) clip. The frame-count VALUES were independently discovered and
 * empirically proven on 2026-07-04 (patch-tested: TT 440->900 streamed the full clip —
 * see fmv_player_streaming.c's "SOLVED 2026-07-04" section); what THIS file adds is the
 * SELECTION MECHANISM — how a movie_id reaches a given case at all.
 *
 * ONE VERIFIED IRREGULARITY (re-checked against raw bytes, not a decode artifact): levels
 * 4 and 5's A-clips are swapped in table order (id 16 -> LEV5A, id 18 -> LEV4A) while
 * their B-clips are not (id 17 -> LEV4B, id 19 -> LEV5B). Level 15 is a special 4-clip
 * case (ids 38-41: A/B/C/D) instead of the usual two.
 *
 * THE TWO LITERAL TRIGGER-SITE CONSTANTS RESOLVE TO CONTENT (inferred, not a traced guard
 * condition): a0=40 -> LEV15C, 3162 frames — the LONGEST clip in the table by a wide
 * margin, strongly suggesting the campaign finale. a0=46 -> LOSE, 281 frames — short, and
 * the literal filename makes the game-over inference almost certain. The third (computed)
 * trigger site passes (a2 & 0xFF) + 41, reaching LEV15D/ALT1/ALT2/ALT3 for a2 = 0..3 —
 * consistent with a variant-ending selector; a2's own source was not traced.
 * ============================================================================ */

#include "re_types.h"
#include <stddef.h>

#define LW(p)   (*(int32_t  *)(p))

#define FMV_MOVIEID_TABLE   0x800B5AA4u  /* u32[47] jr-table, movie_id-indexed            */
#define FMV_MOVIEID_MAX     46            /* sltiu $v0,$s0,0x2F bound; ids 3-9 unused     */
#define FMV_PLAYBACK_CALL   0x800B6D68u  /* per-movie a1=frame_count entry point          */

extern void  ClearImage(int32_t x, int32_t y, int32_t w, int32_t h);   /* PsyQ, named    */
extern void  fmv_playback_start(const char *path, int32_t frame_count,
                                 int32_t arg2, int32_t arg3, int32_t stack_arg);

typedef struct { const char *path; int32_t frame_count; } FmvMovieEntry;

/* Verified byte-for-byte against the pristine FMV.BIN's jr-table targets and each case
 * body's string pointer (lui/addiu) and literal frame-count (addiu $a1,zero,N). The 7
 * DEFAULT slots (ids 3-9) never reach a real case -- see fmv_movie_dispatch() below. */
static const FmvMovieEntry FMV_MOVIE_TABLE[FMV_MOVIEID_MAX + 1] = {
    /*  0 */ { "BUGSFMV3\\tt.str",      440  },
    /*  1 */ { "BUGSFMV3\\dlogo.str",   156  },
    /*  2 */ { "fmv\\ad.str",           1410 },
    /*  3 */ { NULL, 0 },  /* unused -- DEFAULT handler (ClearImage, no STR) */
    /*  4 */ { NULL, 0 },  /* unused -- DEFAULT handler */
    /*  5 */ { NULL, 0 },  /* unused -- DEFAULT handler */
    /*  6 */ { NULL, 0 },  /* unused -- DEFAULT handler */
    /*  7 */ { NULL, 0 },  /* unused -- DEFAULT handler */
    /*  8 */ { NULL, 0 },  /* unused -- DEFAULT handler */
    /*  9 */ { NULL, 0 },  /* unused -- DEFAULT handler */
    /* 10 */ { "BUGSFMV1\\LEV1A.STR",   386  },
    /* 11 */ { "BUGSFMV1\\LEV1B.STR",   485  },
    /* 12 */ { "BUGSFMV1\\LEV2A.STR",   1428 },
    /* 13 */ { "BUGSFMV1\\LEV2B.STR",   1318 },
    /* 14 */ { "BUGSFMV1\\LEV3A.STR",   661  },
    /* 15 */ { "BUGSFMV1\\LEV3B.STR",   1277 },
    /* 16 */ { "BUGSFMV1\\LEV5A.STR",   782  },  /* NOTE: swapped with 18 -- see header */
    /* 17 */ { "BUGSFMV1\\LEV4B.STR",   1514 },
    /* 18 */ { "BUGSFMV1\\LEV4A.STR",   454  },  /* NOTE: swapped with 16 -- see header */
    /* 19 */ { "BUGSFMV1\\LEV5B.STR",   747  },
    /* 20 */ { "BUGSFMV1\\LEV6A.STR",   936  },
    /* 21 */ { "BUGSFMV1\\LEV6B.STR",   1098 },
    /* 22 */ { "BUGSFMV1\\LEV7A.STR",   1532 },
    /* 23 */ { "BUGSFMV1\\LEV7B.STR",   890  },
    /* 24 */ { "BUGSFMV1\\LEV8A.STR",   1083 },
    /* 25 */ { "BUGSFMV1\\LEV8B.STR",   967  },
    /* 26 */ { "BUGSFMV1\\LEV9A.STR",   404  },
    /* 27 */ { "BUGSFMV1\\LEV9B.STR",   830  },
    /* 28 */ { "BUGSFMV2\\LEV10A.STR",  557  },
    /* 29 */ { "BUGSFMV2\\LEV10B.STR",  1166 },
    /* 30 */ { "BUGSFMV2\\LEV11A.STR",  475  },
    /* 31 */ { "BUGSFMV2\\LEV11B.STR",  566  },
    /* 32 */ { "BUGSFMV2\\LEV12A.STR",  704  },
    /* 33 */ { "BUGSFMV2\\LEV12B.STR",  356  },
    /* 34 */ { "BUGSFMV2\\LEV13A.STR",  381  },
    /* 35 */ { "BUGSFMV2\\LEV13B.STR",  715  },
    /* 36 */ { "BUGSFMV2\\LEV14A.STR",  538  },
    /* 37 */ { "BUGSFMV2\\LEV14B.STR",  790  },
    /* 38 */ { "BUGSFMV2\\LEV15A.STR",  315  },  /* level 15: 4-clip special case (A/B/C/D) */
    /* 39 */ { "BUGSFMV2\\LEV15B.STR",  1057 },
    /* 40 */ { "BUGSFMV2\\LEV15C.STR",  3162 },  /* longest clip in the table -- finale?    */
    /* 41 */ { "BUGSFMV2\\LEV15D.STR",  1828 },
    /* 42 */ { "BUGSFMV2\\ALT1.STR",    673  },
    /* 43 */ { "BUGSFMV2\\ALT2.STR",    486  },
    /* 44 */ { "BUGSFMV2\\ALT3.STR",    665  },
    /* 45 */ { "BUGSFMV2\\INTRO.STR",   1750 },
    /* 46 */ { "BUGSFMV2\\LOSE.STR",    281  },  /* filename makes game-over near-certain   */
};

/*
 * 0x800B6250 — FMV.BIN's confirmed entry point. a0 = movie_id (threaded unchanged from
 * the resident trigger site). Bounds-checks, looks up the movie's (path, frame_count) via
 * the on-disc jr-table (modelled here as a plain array read since the table's own targets
 * ARE this function's case bodies, already flattened into FMV_MOVIE_TABLE above), and
 * tail-calls the playback starter with a2=3, a3=0 (the tail's constant args, confirmed
 * for the majority of cases; a few cases set a2/a3 or the stack arg differently -- not
 * separately modelled here, Phase 5).
 */
void fmv_movie_dispatch(int32_t movie_id, int32_t stack_arg)
{
    if ((uint32_t)movie_id >= FMV_MOVIEID_MAX + 1) {
        /* out-of-range: falls through ~178 words ahead to the same DEFAULT path */
        ClearImage(0, 0, 0, 0);  /* args not modelled; the DEFAULT case body only         */
        return;                  /* confirms it clears the screen rather than crashing    */
    }

    const FmvMovieEntry *entry = &FMV_MOVIE_TABLE[movie_id];
    if (entry->path == NULL) {
        /* ids 3-9: valid range, but the jr-table target IS the shared DEFAULT handler
         * (0x800B6574) -- addiu $a0,$sp,24 / zero a1-a3 / jal ClearImage. No STR plays. */
        ClearImage(0, 0, 0, 0);
        return;
    }

    fmv_playback_start(entry->path, entry->frame_count, /*a2=*/3, /*a3=*/0, stack_arg);
}

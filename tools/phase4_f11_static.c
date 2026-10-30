/* Phase 4 F11 (The Tree): the scout-found progression.
 *
 * The row was `external_lead` with two bindings and its own `next` said: "Diff the
 * LEVEL11_1-5 saves to locate the scout-found progression state." That diff found
 * 0x800B4A48 reading 5,4,3,2,1 across the five saves -- the only one of 59 monotonic
 * candidates with a small bounded value. This tool pins the code that drives it.
 *
 * ⚠️ WHICH BLOB. The row's binding says scene 12 -> "overlays LEVEL03_LEVEL/_LEVEL1",
 * taken from the scene-asset graph. That is NOT the resident blob. Region A is a shared
 * swap buffer, so the name proves nothing; comparing a 1 KiB CODE window at 0x800B4400
 * against every candidate blob in both LEVEL11_1.sav and LEVEL11_5.sav matches
 * LEVEL02/LEVEL1.BIN at 100.0% and the next best at 16.0%. This is the second row today
 * where the asset-graph directory name is not the blob that runs (the Council Chamber,
 * D16/F03, was the first).
 *
 * THE MECHANISM
 * -------------
 * A scout is "found" when its actor flags (+0x5C) carry bit 0x1000. Per tick the overlay
 * walks the scouts and counts them:
 *
 *     0x800B42A0  andi v0,v0,0x1000       ; found?
 *     0x800B42A4  beq  -> 0x800B4324      ; not found: skip WITHOUT counting
 *     ...                                 ; found, and first-time conditions met:
 *     0x800B42D4  20(sp) = 2              ;   cinematic-camera FLAGS = 2
 *     0x800B42D8  a0/a1/a2 = [s0+0/4/8]   ;   the scout's own position
 *     0x800B42F4  [0x800B4A4C] = 300      ;   a 300-frame timer
 *     0x800B42F8  jal 0x8004DA94          ;   START THE CINEMATIC CAMERA there
 *     0x800B4318  jal 0x8005044C          ;   play_sound(-13, scout)
 *     0x800B4320  s3++                    ; counted
 *
 * and then publishes the remaining count:
 *
 *     0x800B44A4  v0 = 5
 *     0x800B44B0  subu v0,v0,s3           ; 5 - found
 *     0x800B44B8  [0x800B4A48] = v0       ; *** SCOUTS REMAINING ***
 *
 * ⚠️ CORRECTED 2026-08-04 BY THE LIVE TRACE. An earlier revision of this file claimed the
 * found bit is a ONE-SHOT cleared at 0x800B449C. It is not. That clear runs on `s1`
 * AFTER s1 is reassigned at 0x800B4340/44 to 0x800A1850 -- a different actor, not a
 * scout. Live (tools/phase4_f11_find_event.py) the bit is set once per scout and NEVER
 * cleared: it is a PERSISTENT found marker, which is what makes `5 - count` stable.
 *
 * Init is 6, not 5 (0x800B3CB4), i.e. "none found yet" is distinguishable from "5 left".
 * A per-count byte table at 0x800B49EC is indexed by the remaining count and fed to
 * sfx_dispatch 0x80050994 (0x800B458C..0x800B459C) -- a per-scout audio cue.
 *
 * THE FIND EVENT (live, tools/phase4_f11_find_event.py): bit 0x1000 is set by
 * 0x8004B464 -- `ori v0,v0,0x1000` inside actor_player_contact_resolver 0x8004ABF4.
 * FINDING A SCOUT IS TOUCHING IT. That is generic resident contact code, not
 * scout-specific, so bit 0x1000 means "the player has contacted me" campaign-wide --
 * which also settles D16's open question about the mosquito callback's use of the same
 * bit: one shared convention, not a coincidental reuse.
 *
 * THE EXIT GATE (0x800B43EC..0x800B4424), which is the stage objective:
 *
 *     lhu  v0,0x5C(s1)          ; s1 = 0x800A1850 = DOT (actor id 14, verified live)
 *     andi v0,v0,0x1000         ; has the player contacted Dot?
 *     beq  -> 0x800B44A4        ; no -> skip (that path CLEARS Dot's bit)
 *     v0 = 5
 *     bne  s3,v0 -> 0x800B4458  ; *** not all five scouts -> REFUSE ***
 *     lh   v0,[0x800823A0]
 *     bne  v0,zero -> 0x800B4458; already latched -> once-only
 *     [0x800823A0] = 1          ; *** THE LEVEL EXIT ***
 *
 * `s3` is the same live count of scouts carrying the contact bit, so the refusal is
 * literally "you have not found all five". The operator described exactly this behaviour
 * ("less than that and touching Dot will not take you out of the level"); this is that
 * sentence as an instruction.
 *
 * So DOT's contact bit is the ONE-SHOT (consumed at 0x800B449C, one attempt per touch)
 * while the SCOUTS' bits are persistent. An earlier revision of this file attributed that
 * clear to a scout -- wrong actor, right instruction.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_f11_static.c -o /tmp/f11 \
 *     && /tmp/f11 REBUILD/files/LEVEL02/LEVEL1.BIN
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define REGION_A_BASE 0x800B39A0u
#define COUNTER       0x800B4A48u
#define SFX_TABLE     0x800B49ECu
#define TIMER         0x800B4A4Cu

static uint8_t *blob;
static size_t blob_size;

static int u32_at(uint32_t va, uint32_t *out)
{
    size_t off;
    if (va < REGION_A_BASE) return 0;
    off = (size_t)(va - REGION_A_BASE);
    if (off + 4 > blob_size) return 0;
    *out = (uint32_t)blob[off] | ((uint32_t)blob[off+1] << 8) |
           ((uint32_t)blob[off+2] << 16) | ((uint32_t)blob[off+3] << 24);
    return 1;
}

struct pin { uint32_t va, word; const char *role; };

static const struct pin pins[] = {
    /* the counter: init, derivation, publication */
    {0x800B3CB4u, 0xAC224A48u, "init: [0x800B4A48] = 6 (v0 set at 0x800B3CAC)"},
    {0x800B3CACu, 0x24020006u, "init constant 6 -- NOT 5, so 'none found' is distinct"},
    {0x800B44A4u, 0x24020005u, "v0 = 5 (the scout total)"},
    {0x800B44B0u, 0x00531023u, "subu v0,v0,s3  -- remaining = 5 - found"},
    {0x800B44B8u, 0xAC224A48u, "*** publish [0x800B4A48] = scouts remaining ***"},

    /* what counts as found */
    {0x800B42A0u, 0x30421000u, "andi v0,v0,0x1000 -- the FOUND bit in actor flags +0x5C"},
    {0x800B42A4u, 0x1040001Fu, "beq -> skip WITHOUT counting when the bit is clear"},
    {0x800B4320u, 0x26730001u, "s3++ -- a found scout is counted"},
    {0x800B4344u, 0x26311850u, "s1 = 0x800A1850 = DOT (actor id 14, read live)"},
    {0x800B449Cu, 0x3042EFFFu, "andi 0xEFFF -- clears DOT's contact bit, not a scout's: "
                                "each touch of Dot is one attempt"},

    /* the exit gate: touch Dot AND have all five */
    {0x800B43ECu, 0x9622005Cu, "lhu Dot's flags +0x5C"},
    {0x800B43F4u, 0x30421000u, "andi 0x1000 -- has the player CONTACTED Dot?"},
    {0x800B43F8u, 0x1040002Au, "no contact -> skip to the clear path"},
    {0x800B43FCu, 0x24020005u, "v0 = 5 (delay slot)"},
    {0x800B4400u, 0x16620015u, "*** bne s3,5 -- REFUSE unless all five scouts are found"},
    {0x800B440Cu, 0x844223A0u, "lh the goal latch"},
    {0x800B4414u, 0x14400010u, "already latched -> skip (once-only)"},
    {0x800B4424u, 0xA42223A0u, "*** [0x800823A0] = 1 -- THE LEVEL EXIT ***"},

    /* finding one starts a cinematic camera at the scout */
    {0x800B42D4u, 0xAFA20014u, "20(sp) = 2 -- cinematic-camera FLAGS argument"},
    {0x800B42F4u, 0xAC224A4Cu, "[0x800B4A4C] = 300 -- the post-find timer"},
    {0x800B42F8u, 0x0C0136A5u, "jal 0x8004DA94 -- start the cinematic camera"},
    {0x800B4318u, 0x0C014113u, "jal 0x8005044C play_sound"},

    /* the per-count audio cue */
    {0x800B458Cu, 0x8C424A48u, "lw the remaining count"},
    {0x800B4598u, 0x902449ECu, "lbu a0,[0x800B49EC + count] -- per-count byte"},
    {0x800B459Cu, 0x0C014265u, "jal 0x80050994 sfx_dispatch"},

    /* this blob is the one that reads the cinematic-camera flag (D16 census) */
    {0x800B4560u, 0x94420BEEu, "lhu [0x80090BEE] -- the cinematic-camera flags word"},
    {0x800B4568u, 0x30420001u, "andi 1 -- gated on the camera being ACTIVE"},
};

int main(int argc, char **argv)
{
    FILE *f;
    long n;
    size_t i, ok = 0, total = sizeof pins / sizeof pins[0];

    if (argc != 2) { fprintf(stderr, "usage: %s <LEVEL02/LEVEL1.BIN>\n", argv[0]); return 2; }
    f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 2; }
    n = ftell(f);
    if (n <= 0) { fclose(f); return 2; }
    rewind(f);
    blob_size = (size_t)n;
    blob = malloc(blob_size);
    if (!blob || fread(blob, 1, blob_size, f) != blob_size) { fclose(f); return 2; }
    fclose(f);

    printf("blob %s  (%zu bytes, VA 0x%08X..0x%08zX)\n\n", argv[1], blob_size,
           REGION_A_BASE, (size_t)REGION_A_BASE + blob_size);
    for (i = 0; i < total; i++) {
        uint32_t got = 0;
        int have = u32_at(pins[i].va, &got);
        int good = have && got == pins[i].word;
        ok += (size_t)good;
        printf("  %s 0x%08" PRIx32 "  want %08" PRIx32 "  got %08" PRIx32 "  %s\n",
               good ? "ok  " : "FAIL", pins[i].va, pins[i].word, got, pins[i].role);
    }
    printf("\n  %zu/%zu pins OK\n", ok, total);
    if (ok != total) { free(blob); return 1; }

    puts("");
    puts("F11 scouts: found = actor flags(+0x5C) bit 0x1000, SET BY PLAYER CONTACT");
    puts("  (0x8004B464 `ori 0x1000` inside actor_player_contact_resolver 0x8004ABF4),");
    puts("  and PERSISTENT -- never cleared on a scout.");
    puts("  [0x800B4A48] = 5 - (number found), init 6. Finding one starts a CINEMATIC");
    puts("  CAMERA (flags=2) at that scout's position with a 300-frame timer, and a");
    puts("  per-count byte table at 0x800B49EC feeds sfx_dispatch.");
    puts("  ⚠️ The resident blob is LEVEL02/LEVEL1.BIN -- NOT the LEVEL03_* the row's");
    puts("  scene-asset binding names. Verified by a 1 KiB code-window compare (100.0%)");
    puts("  against both LEVEL11_1.sav and LEVEL11_5.sav.");
    free(blob);
    return 0;
}

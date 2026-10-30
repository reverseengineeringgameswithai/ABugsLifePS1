/* music_start @ 0x8004699c (292 B, gp) - start XA streamed music for a packed id.
 * file = packed_id >> 3 (AUDIO(file+1)); channel = packed_id & 7. */

#if ABL_PSYQ_DECL_PROFILE != 3
#include "abl/psyq_decl.h"
#endif

struct xa_desc { int start; int flag; int rsv; };
extern struct xa_desc g_800772cc[];
extern int g_800821b8;
extern int g_80082478;
extern int g_80082384;
extern int g_80082408;
extern int g_800821b4;

int music_start(int packed_id)
{
    int idx = packed_id >> 3;
    int chan = packed_id & 7;
    int flag = g_800772cc[idx].flag;
    int start;

    /* The retail object reserves 24 outgoing-argument bytes before its locals.
     * Keeping that clean-room-observed layout explicit reproduces its frame. */
    struct {
        unsigned char psyq_outgoing[24];
        CdlLOC loc;
        unsigned char pad0[4];
        unsigned char mode;
        unsigned char pad1[7];
        CdlLOC loc2;
        unsigned char pad2[4];
        CdlFILTER filt;
        unsigned char pad3[6];
    } frame;

    g_80082478 = 0;
    g_800821b8 = idx;
    if (flag == 0)
        return 0;

    frame.mode = 0xe8;
    CdControlB(0xe, &frame.mode, 0);
    CdControlF(9, 0);

    g_80082478 = g_80082478 | 1;
    frame.loc.minute = 0;
    frame.loc.second = 0;
    frame.loc.sector = 0;
    frame.loc.track = 0;
    CdMix(&frame.loc);
    CdControl(0xc, 0, 0);

    g_80082384 = 0xa;
    start = g_800772cc[g_800821b8].start;
    SsSetSerialVol(0, 0x7f, 0x7f);

    frame.filt.file = 1;
    frame.filt.chan = (unsigned char)chan;
    g_80082408 = chan;
    CdControlF(0xd, (unsigned char *)&frame.filt);

    CdIntToPos(start, &frame.loc2);
    g_800821b4 = start;
    CdControlF(0x1b, (unsigned char *)&frame.loc2);
}

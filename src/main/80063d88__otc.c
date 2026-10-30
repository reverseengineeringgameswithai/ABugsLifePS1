/* _otc @ 0x80063D88 - libgpu: clear an ordering table of `arg1` entries ending at
 * `arg0` using the OTC DMA channel. Enables the channel in the DMA control word
 * (*g_8007fcb8 |= 0x08000000), programs the channel registers through the pointer
 * globals (madr *g_8007fcac = last entry, bcr *g_8007fcb0 = count, chcr
 * *g_8007fcb4 = 0x11000002 reverse-clear start), kicks sub_80064f28, then polls
 * the chcr busy bit 0x01000000 with sub_80064f5c as the timeout check; returns
 * the count on completion or -1 on timeout. volatile targets keep every
 * re-load/re-store; the `ofs` temp keeps (count*4 - 4) grouped as retail. */
typedef int s32;

extern volatile s32 *g_8007fcac;
extern volatile s32 *g_8007fcb0;
extern volatile s32 *g_8007fcb4;
extern volatile s32 *g_8007fcb8;
extern int sub_80064f28(void);
extern int sub_80064f5c(void);

s32 _otc(s32 arg0, s32 arg1)
{
    volatile s32 *ctrl;
    s32 ofs;

    ctrl = g_8007fcb8;
    *ctrl |= 0x08000000;
    *g_8007fcb4 = 0;
    ofs = (arg1 * 4) - 4;
    *g_8007fcac = arg0 + ofs;
    *g_8007fcb0 = arg1;
    *g_8007fcb4 = 0x11000002;
    sub_80064f28();
    while (*g_8007fcb4 & 0x01000000) {
        if (sub_80064f5c() != 0)
            return -1;
    }
    return arg1;
}

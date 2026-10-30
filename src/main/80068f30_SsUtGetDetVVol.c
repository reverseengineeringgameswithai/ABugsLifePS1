/* SsUtGetDetVVol @ 0x80068f30 - read a voice's detailed L/R volume; -1 if out of range. */
extern int g_80080ec8;
short SsUtGetDetVVol(int idx, short *lvol, short *rvol)
{
    if ((unsigned int)(idx & 0xffff) < 24) {
        int off = (short)idx * 16;

        *lvol = *(unsigned short *)(off + g_80080ec8);
        *rvol = *(unsigned short *)(off + g_80080ec8 + 2);
        return 0;
    }
    return -1;
}

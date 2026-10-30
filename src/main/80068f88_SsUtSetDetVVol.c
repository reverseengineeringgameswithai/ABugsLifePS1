/* SsUtSetDetVVol @ 0x80068f88 - set a voice's detailed L/R volume + enable flag. */
extern short g_8009fbe8[];
extern unsigned char g_80090850[];
short SsUtSetDetVVol(int idx, short lvol, short rvol)
{
    if ((unsigned int)(idx & 0xffff) < 24) {
        short id = idx;
        unsigned char f;

        *(short *)((char *)g_8009fbe8 + id * 16 + 2) = rvol;
        f = g_80090850[id];
        *(short *)((char *)g_8009fbe8 + id * 16) = lvol;
        g_80090850[id] = f | 3;
        return 0;
    }
    return -1;
}

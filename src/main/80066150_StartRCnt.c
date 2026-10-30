/* StartRCnt @ 0x80066150 - enable a root-counter's mode bits; returns spec<3. */
extern unsigned int *g_80080e48;   /* root-counter register block pointer */
extern unsigned int g_80080e50[];  /* per-spec enable-bit table */
int StartRCnt(int spec)
{
    int idx = spec & 0xffff;
    g_80080e48[1] |= g_80080e50[idx];
    return idx < 3;
}

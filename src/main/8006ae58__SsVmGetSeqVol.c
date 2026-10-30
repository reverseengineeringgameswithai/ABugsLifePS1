/* _SsVmGetSeqVol @ 0x8006ae58 - read a sequence's L/R channel volume (offset 88/90)
 * from its VM record; returns the (16-bit) sequence id. */
extern int g_800b01a0[];
extern short g_8009fa1e;
short _SsVmGetSeqVol(int seq, short *lvol, short *rvol)
{
    int base = g_800b01a0[seq & 0xff];
    short *pf = &g_8009fa1e;
    char *entry;

    *pf = seq;
    entry = (char *)base + ((seq & 0xff00) >> 8) * 176;
    *lvol = *(unsigned short *)(entry + 88);
    *rvol = *(unsigned short *)(entry + 90);
    return *pf;
}

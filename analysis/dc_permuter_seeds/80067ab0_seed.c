extern int g_800b01a0[];
void _SsSndReplay(int seq, int sep)
{
    int *slot = &g_800b01a0[(short)seq];
    int off = (short)sep * 176;
    *(char *)((char *)*slot + off + 20) = 1;
    *(int *)(off + (int)*slot + 152) &= ~8;
}

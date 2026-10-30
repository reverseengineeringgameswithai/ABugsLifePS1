extern short *g_80080e4c;
int ResetRCnt(int spec)
{
    int idx = spec & 0xffff;
    if (idx < 3) { *(short *)((char *)g_80080e4c + idx * 16) = 0; return 1; }
    return 0;
}

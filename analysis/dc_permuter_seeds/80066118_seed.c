extern short *g_80080e4c;
int GetRCnt(int spec)
{
    int idx = spec & 0xffff;
    if (idx < 3) return *(unsigned short *)((char *)g_80080e4c + idx * 16);
    return 0;
}

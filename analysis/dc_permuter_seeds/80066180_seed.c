extern unsigned int *g_80080e48;
extern unsigned int g_80080e50[];
int StopRCnt(int spec)
{
    g_80080e48[1] &= ~g_80080e50[spec & 0xffff];
    return 1;
}

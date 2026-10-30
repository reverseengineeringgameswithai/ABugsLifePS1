extern int g_80081060, g_800814e0;
void SpuSetTransferMode(int mode)
{
    int flag;
    if (mode == 0) flag = 0;
    else if (mode == 1) flag = 1;
    else flag = 0;
    g_80081060 = mode;
    g_800814e0 = flag;
}

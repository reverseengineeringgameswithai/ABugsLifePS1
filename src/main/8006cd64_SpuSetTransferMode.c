/* SpuSetTransferMode @ 0x8006cd64 - record the SPU transfer mode + derived DMA flag.
 * `switch` keeps the 3 branches un-merged to match the original codegen. */
extern int g_80081060, g_800814e0;
void SpuSetTransferMode(int mode)
{
    int flag;
    switch (mode) { case 0: flag = 0; break; case 1: flag = 1; break; default: flag = 0; }
    g_80081060 = mode;
    g_800814e0 = flag;
}

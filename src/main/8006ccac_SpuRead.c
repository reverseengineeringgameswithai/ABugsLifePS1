/* SpuRead @ 0x8006ccac - start an SPU-RAM read, clamping the size; returns the size used. */
extern int sub_8006c074(int addr, int size);
extern int g_800814fc;
extern int g_800814f8;
int SpuRead(int addr, unsigned int size)
{
    if (size > 0x7eff0)
        size = 0x7eff0;
    sub_8006c074(addr, size);
    if (g_800814fc == 0)
        g_800814f8 = 0;
    return size;
}

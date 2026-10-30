/* SpuInitMalloc @ 0x8006c3e0 - initialize the SPU-RAM allocator over `num` blocks. */
extern int g_800814ec;
extern int g_80081528, g_80081524, g_80081520;
int SpuInitMalloc(int num, int *top)
{
    if (num > 0) {
        int shift = g_800814ec;
        top[0] = 0x40001010;
        g_80081528 = (int)top;
        g_80081524 = 0;
        g_80081520 = num;
        top[1] = (0x10000 << shift) - 0x1010;
        return num;
    }
    return 0;
}

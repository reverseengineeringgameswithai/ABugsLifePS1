/* StClearRing @ 0x8007094c - reset the CD streaming ring-buffer bookkeeping. */
extern int g_800b3980;
extern int g_800a7e3c, g_800a7e20, g_800a7e1c, g_8009e738;
extern int g_800911c8, g_800894e0;
extern short g_800902dc;
extern void sub_80070c60(int start, int count);
void StClearRing(void)
{
    int count = g_800b3980;

    g_800a7e3c = 0;
    g_800a7e20 = 0;
    g_800a7e1c = 0;
    g_8009e738 = 0;
    sub_80070c60(0, count);
    g_800911c8 = 0;
    g_800902dc = 0;
    g_800894e0 = 0;
}

/* memsets a 3584-byte pool at 0x800B0D18, then clears two reset flags. */
extern void memset(void *dst, int c, int n);
extern int g_800b0d18[896];
extern int g_8008234c[4];
extern int g_80082240;

void clear_gameplay_pool_on_reset(void)
{
    memset(g_800b0d18, 0, 3584);
    g_8008234c[0] = 0;
    g_80082240 = 0;
}

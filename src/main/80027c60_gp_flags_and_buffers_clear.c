/* gp_flags_and_buffers_clear - zero 7 gp halfwords, memset two buffers. */
extern short g_80082244, g_80082264, g_800822c4, g_800823c8,
             g_800824c8, g_800823e8, g_800824e0;
extern char g_800b0230[];
extern char g_8009b3a8[];
extern void *memset(void *dst, int c, int n);

void gp_flags_and_buffers_clear(void)
{
    g_80082244 = 0;
    g_80082264 = 0;
    g_800822c4 = 0;
    g_800823c8 = 0;
    g_800824c8 = 0;
    g_800823e8 = 0;
    g_800824e0 = 0;
    memset(g_800b0230, 0, 128);
    memset(g_8009b3a8, 0, 512);
}

/* SetGraphDebug @ 0x800623d4 - set the libgpu debug level; returns the previous one. */
extern unsigned char g_8007fbca;
extern void (*g_8007fbc4)(void *s, int a, int b, int c);
extern unsigned char g_8007fbc8, g_8007fbcb;
extern char g_8001bf84[];
int SetGraphDebug(int level)
{
    unsigned char *p = &g_8007fbca;
    int old = *p;

    *p = level;
    if (level & 0xff)
        g_8007fbc4(g_8001bf84, level & 0xff, g_8007fbc8, g_8007fbcb);
    return old;
}

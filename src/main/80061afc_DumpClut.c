/* DumpClut @ 0x80061afc - print a CLUT id (x/y position) via the debug dump handler. */
extern void (*g_8007fbc4)(void *s, int a, int b);
extern char g_8001be4c[];
void DumpClut(int clut)
{
    g_8007fbc4(g_8001be4c, (clut & 0x3f) << 4, (unsigned int)(clut & 0xffff) >> 6);
}

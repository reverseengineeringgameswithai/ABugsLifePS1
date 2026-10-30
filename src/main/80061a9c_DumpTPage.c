/* DumpTPage @ 0x80061a9c - decode a texpage id and print it via the debug dump handler. */
extern void (*g_8007fbc4)(void *s, int a, int b, int c, int d);
extern char g_8001be34[];
void DumpTPage(int tp)
{
    unsigned int t = tp & 0xffff;
    int base = ((t << 4) & 0x100) + ((t >> 2) & 0x200);

    g_8007fbc4(g_8001be34, (t >> 7) & 3, (t >> 5) & 3, (t << 6) & 0x7c0, base);
}

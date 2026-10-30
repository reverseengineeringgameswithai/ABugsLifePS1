/* CD_initintr @ 0x8006f004 - reset CD interrupt state and install its handler. */
extern int g_800818c8, g_800818c4, g_800818d8, g_800818d4;
extern void sub_800653d4(void);
extern void sub_80065404(int prio, int handler);
extern void sub_8006f5ac();
void CD_initintr(void)
{
    g_800818c8 = 0;
    g_800818c4 = 0;
    g_800818d8 = 0;
    g_800818d4 = 0;
    sub_800653d4();
    sub_80065404(2, (int)sub_8006f5ac);
}

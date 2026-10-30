/* startIntrVSync @ 0x80065af4 - install the VSync interrupt handler; returns its address. */
extern int *g_80080e18;
extern int g_80080e14;
extern void sub_80065bf0(void *p, int n);
extern void sub_80065404(int prio, int handler);
extern int g_80080df4[];
extern void sub_80065b4c();
extern void sub_80065bc4();
int startIntrVSync(void)
{
    *g_80080e18 = 263;
    g_80080e14 = 0;
    sub_80065bf0(g_80080df4, 8);
    sub_80065404(0, (int)sub_80065b4c);
    return (int)sub_80065bc4;
}

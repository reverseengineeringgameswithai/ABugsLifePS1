/* CdReadBreak @ 0x800705FC - libcd: abort an in-flight CdRead. If bit 0 of the
 * stream-mode word g_80081c10 is set, stop the retry timer (sub_8006dd14(0));
 * clear the read-active flag g_80081bf4; restore the saved sync/ready callbacks
 * g_80081c04 / g_80081c08 through their setters; if streaming, also restore the
 * data callback g_80081c0c; finally issue CD command 9 (Pause) via sub_8006da20.
 * Byte-exact needs &g_80081c10 held in a local across the calls (re-read through
 * s0 both times) and volatile on g_80081bf4/g_80081c04 to pin the store-before-
 * load order around the first setter call. */
extern volatile int g_80081bf4;
extern volatile int g_80081c04;
extern int g_80081c08;
extern int g_80081c0c;
extern int g_80081c10;
extern int sub_8006dd14(int);
extern int sub_8006d8b8(int);
extern int sub_8006d8d0(int);
extern int sub_8006dcf0(int);
extern int sub_8006da20(int, int);

void CdReadBreak(void)
{
    int *flags;

    flags = &g_80081c10;
    if (*flags & 1)
        sub_8006dd14(0);
    g_80081bf4 = 0;
    sub_8006d8b8(g_80081c04);
    sub_8006d8d0(g_80081c08);
    if (*flags & 1)
        sub_8006dcf0(g_80081c0c);
    sub_8006da20(9, 0);
}

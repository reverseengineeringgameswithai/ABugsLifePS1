/* ss_seq_tick_every_other_dispatch - $v0-input tick gate. */
extern int g_80080ec4;
extern void (*g_80080eb8)(void);

void ss_seq_tick_every_other_dispatch(void)
{
    register int flag asm("$2");

    if (flag == 0) {
        g_80080ec4 = 1;
    } else {
        void (*fn)(void) = g_80080eb8;
        g_80080ec4 = 0;
        fn();
    }
}

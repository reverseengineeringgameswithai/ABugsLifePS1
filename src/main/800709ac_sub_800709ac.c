/* sub_800709ac @ 0x800709AC - inside a critical section (EnterCriticalSection
 * 0x80065fbc / ExitCriticalSection 0x80065fcc), stop both halves of the active
 * audio backend - the pair (sub_800b9a28, sub_800b9a14) when mode g_800818e8 == 1,
 * else (sub_8006dcf0, sub_8006d8d0) - then clear the two byte flags pointed to by
 * g_80081c28 / g_80081c34. volatile store targets keep the final flag write out
 * of the ExitCriticalSection call's delay slot, as retail. */
extern int g_800818e8;
extern volatile signed char *g_80081c28;
extern volatile signed char *g_80081c34;
extern int sub_80065fbc(void);
extern int sub_80065fcc(void);
extern int sub_800b9a28(int);
extern int sub_800b9a14(int);
extern void sub_8006dcf0(int);
extern void sub_8006d8d0(int);

void sub_800709ac(void)
{
    sub_80065fbc();
    if (g_800818e8 == 1) {
        sub_800b9a28(0);
        sub_800b9a14(0);
    } else {
        sub_8006dcf0(0);
        sub_8006d8d0(0);
    }
    *g_80081c28 = 0;
    *g_80081c34 = 0;
    sub_80065fcc();
}

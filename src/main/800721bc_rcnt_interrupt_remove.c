/* rcnt_interrupt_remove @ 0x800721bc - tear down the root-counter interrupt hooks. */
extern void sub_80065fbc(void);
extern void sub_8006606c(int a, int b);
extern void sub_800667fc(int a, int b);
extern void sub_80065fcc(void);
extern int g_80089008[];
void rcnt_interrupt_remove(void)
{
    sub_80065fbc();
    sub_8006606c(3, 1);
    sub_800667fc(2, (int)g_80089008);
    sub_80065fcc();
}

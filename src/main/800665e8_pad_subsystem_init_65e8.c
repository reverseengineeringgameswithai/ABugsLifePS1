/* pad_subsystem_init_65e8 @ 0x800665E8 — init pad, returns 1. */
extern void StartPAD2(void);
extern void ChangeClearPAD(int);
extern void sub_8006680c(void);
int pad_subsystem_init_65e8(void)
{
    StartPAD2();
    ChangeClearPAD(0);
    sub_8006680c();
    return 1;
}

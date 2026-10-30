extern void sub_8006f004(void);
extern int sub_8006f054(void);
extern int sub_8006ef10(void);
int CdReset(int mode)
{
    if (mode == 2) { sub_8006f004(); return 1; }
    if (sub_8006f054() != 0) return 0;
    if (mode != 1) return 1;
    if (sub_8006ef10() != 0) return 0;
    return 1;
}

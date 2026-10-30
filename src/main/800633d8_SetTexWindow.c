/* SetTexWindow @ 0x800633d8 - build a GP0(0xE2) texture-window primitive. */
extern int sub_80063c3c(int win);
void SetTexWindow(unsigned char *prim, int win)
{
    prim[3] = 2;
    *(int *)(prim + 4) = sub_80063c3c(win);
    *(int *)(prim + 8) = 0;
}

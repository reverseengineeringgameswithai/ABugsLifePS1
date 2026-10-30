/* SetDrawMode @ 0x80063508 - build a GP0(0xE1) draw-mode primitive + texture window. */
extern int get_mode(int dfe, int dtd, int tpage);
extern int sub_80063c3c(int win);
void SetDrawMode(unsigned char *prim, int dfe, int dtd, int tpage, int texwin)
{
    prim[3] = 2;
    *(int *)(prim + 4) = get_mode(dfe, dtd, tpage & 0xffff);
    *(int *)(prim + 8) = sub_80063c3c(texwin);
}

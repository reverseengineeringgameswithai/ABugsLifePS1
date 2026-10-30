/* SetDrawOffset @ 0x80063498 - build a GP0(0xE5) draw-offset primitive from an (x,y) pair. */
extern int sub_80063bf8(int x, int y);
void SetDrawOffset(unsigned char *prim, short *ofs)
{
    prim[3] = 2;
    *(int *)(prim + 4) = sub_80063bf8(ofs[0], ofs[1]);
    *(int *)(prim + 8) = 0;
}

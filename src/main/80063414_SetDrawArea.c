/* SetDrawArea @ 0x80063414 - build the GP0(0xE3/0xE4) draw-area clip primitives. */
extern int sub_80063a60(int x, int y);
extern int sub_80063b2c(int x, int y);
void SetDrawArea(unsigned char *prim, unsigned short *area)
{
    prim[3] = 2;
    *(int *)(prim + 4) = sub_80063a60((short)area[0], (short)area[1]);
    *(int *)(prim + 8) = sub_80063b2c((short)(area[0] + area[2] - 1),
                                      (short)(area[1] + area[3] - 1));
}

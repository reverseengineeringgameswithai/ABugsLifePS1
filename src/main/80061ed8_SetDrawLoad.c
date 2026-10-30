/* SetDrawLoad @ 0x80061ed8 - build a VRAM load primitive sized to the rect area. */
void SetDrawLoad(unsigned char *prim, void *rect)
{
    short *r = (short *)rect;
    int *ri = (int *)rect;
    int area = r[2] * r[3];
    int half = (area + 1) / 2;
    int len = half + 4;

    if ((unsigned int)half >= 13)
        len = 0;
    prim[3] = len;
    *(int *)(prim + 4) = 0xa0000000;
    *(int *)(prim + 8) = ri[0];
    *(int *)(prim + 12) = ri[1];
    *(int *)(prim + (len << 2)) = 0x1000000;
}

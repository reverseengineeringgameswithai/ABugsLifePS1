void SetDrawMove(unsigned char *prim, int *src, int arg2, int arg3)
{
    short *s = (short *)src;
    int len = (s[2] != 0 && s[3] != 0) ? 5 : 0;
    *(int *)(prim + 4) = 0x1000000;
    *(int *)(prim + 8) = 0x80000000;
    prim[3] = len;
    *(int *)(prim + 16) = (arg3 << 16) | (arg2 & 0xffff);
    *(int *)(prim + 12) = src[0];
    *(int *)(prim + 20) = src[1];
}

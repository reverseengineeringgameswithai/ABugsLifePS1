extern void SetDrawTPage(unsigned char *p, int dfe, int dtd, int tpage);
void SetDrawTPage(unsigned char *p, int dfe, int dtd, int tpage)
{
    unsigned int hi, lo;
    p[3] = 1;
    hi = 0xe1000000;
    if (dtd) hi |= 0x200;
    lo = tpage & 0x9ff;
    if (dfe) lo |= 0x400;
    *(unsigned int *)(p + 4) = hi | lo;
}

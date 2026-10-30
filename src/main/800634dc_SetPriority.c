/* SetPriority @ 0x800634dc - build a GP0(0xE6) mask-drawing primitive. */
void SetPriority(unsigned char *p, int a1, int a2)
{
    unsigned int v;
    p[3] = 2;
    v = 0xe6000000;
    if (a1) v |= 2;
    if (a2) v |= 1;
    *(unsigned int *)(p + 4) = v;
    *(unsigned int *)(p + 8) = 0;
}

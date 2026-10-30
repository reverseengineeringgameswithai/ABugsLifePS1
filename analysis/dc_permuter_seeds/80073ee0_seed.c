extern void pad_direct_clear_info(unsigned char *p);
void pad_direct_clear_info(unsigned char *p)
{
    unsigned char *q;
    int i;
    if (p[73] == 0) return;
    p[73] = 0; p[70] = 0;
    *(short *)(p + 230) = 0;
    *(int *)(p + 20) = 0; *(int *)(p + 24) = 0;
    p[227] = 0; p[228] = 0;
    *(short *)(p + 230) = 0;
    p[233] = 0; p[234] = 0;
    *(int *)(p + 0) = 0; *(int *)(p + 4) = 0; *(int *)(p + 8) = 0;
    q = p + 93;
    for (i = 5; i >= 0; i--) *q++ = 255;
}

/* _padGetActSize @ 0x80072e80 - compute the actuator-config transfer size. */
int _padGetActSize(unsigned char *p)
{
    int a = ((p[227] + 1) >> 1) << 2;
    int b = ((p[233] * 5 + 3) & 0xffc) + 4;

    return a + b + *(unsigned short *)(p + 236);
}

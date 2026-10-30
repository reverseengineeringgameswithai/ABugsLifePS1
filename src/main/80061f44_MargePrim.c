/* MargePrim @ 0x80061f44 - merge p1 into p0's length byte; -1 if it would exceed 0x10. */
int MargePrim(unsigned char *p0, unsigned char *p1)
{
    int len = p0[3] + p1[3] + 1;

    if (len >= 0x11)
        return -1;
    p0[3] = len;
    *(int *)p1 = 0;
    return 0;
}

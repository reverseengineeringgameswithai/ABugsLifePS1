extern int get_ofs(int x, int y);
extern unsigned char g_8007fbc8;
int get_ofs(int x, int y)
{
    int hi, lo;
    if ((unsigned int)(g_8007fbc8 - 1) < 2) {
        hi = (y & 0xfff) << 12;
        lo = x & 0xfff;
    } else {
        hi = (y & 0x7ff) << 11;
        lo = x & 0x7ff;
    }
    return hi | (lo | 0xe5000000);
}

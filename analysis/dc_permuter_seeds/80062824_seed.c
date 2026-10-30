/* ClearImage2 @ 0x80062824 - like ClearImage but sets the semi-transparent
 * (STP) top bit in the fill colour before dispatching the GPU fill. */
extern void sub_80062668(void *env, unsigned char *rect);
extern void *g_8001c02c;
extern void **g_8007fbc0;
int ClearImage2(unsigned char *rect, unsigned char b, int g, int r)
{
    int color;
    int (*fn)(void *, unsigned char *, int, int);
    sub_80062668(&g_8001c02c, rect);
    color = 0x80000000 | ((r & 0xff) << 16) | ((g & 0xff) << 8) | (b & 0xff);
    fn = (int (*)(void *, unsigned char *, int, int))g_8007fbc0[2];
    return fn(g_8007fbc0[3], rect, 8, color);
}

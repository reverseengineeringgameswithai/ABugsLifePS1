/* ClearImage @ 0x80062790 - queue a rectangle-fill to (b,g,r) via the GPU
 * dispatch table: prep the fill primitive then call the table's fill entry. */
extern void sub_80062668(void *env, unsigned char *rect);
extern void *g_8001c02c;
extern void **g_8007fbc0;
int ClearImage(unsigned char *rect, unsigned char b, int g, int r)
{
    int color;
    int (*fn)(void *, unsigned char *, int, int);
    sub_80062668(&g_8001c02c, rect);
    color = ((r & 0xff) << 16) | ((g & 0xff) << 8) | (b & 0xff);
    fn = (int (*)(void *, unsigned char *, int, int))g_8007fbc0[2];
    return fn(g_8007fbc0[3], rect, 8, color);
}

/* FntLoad @ 0x80060FF4 - libgpu: upload the debug-font CLUT + 128x32 texture from
 * the staging buffer at g_8007f170 (CLUT data first, pixel data at +512) to VRAM
 * at (x, y+0x80) / (x, y), reset the font stream counter g_8007f168, then clear
 * the 0x180-byte font state block at g_8007efe8 via sub_8005f7ac.
 * Byte-exact needs `base` held in a local across both calls (third callee-saved
 * register) with the second call addressing base + 512. */
extern short g_80086914;
extern short g_80086910;
extern int g_8007f168;
extern char g_8007f170[];
extern char g_8007efe8[];

extern int sub_80060e58(void *clut, int x, int y);
extern short sub_80060d04(void *rect, int a, int b, int x, int y, int w, int h);
extern int sub_8005f7ac(void *dst, int val, int len);

void FntLoad(int x, int y)
{
    char *base;

    base = g_8007f170;
    g_80086914 = sub_80060e58(base, x, y + 0x80);
    g_80086910 = sub_80060d04(base + 512, 0, 0, x, y, 0x80, 0x20);
    g_8007f168 = 0;
    sub_8005f7ac(g_8007efe8, 0, 0x180);
}

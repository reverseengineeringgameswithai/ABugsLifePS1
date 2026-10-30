/* LoadClut @ 0x80060df0 - upload a CLUT (width 256) to VRAM and return its packed id. */
extern void sub_800628c0(void *rect, void *data);
extern int sub_80061a84(int x, int y);
int LoadClut(void *clut, int x, int y)
{
    struct { short x, y, w, h; } rect;

    rect.x = x;
    rect.y = y;
    rect.w = 256;
    rect.h = 1;
    sub_800628c0(&rect, clut);
    return sub_80061a84(x, y) & 0xffff;
}

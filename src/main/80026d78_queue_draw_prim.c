/* queue_draw_prim - append a DR_MODE prim (256x256 texwindow), link into OT+440, advance write ptr by 12. */
struct rect26 { short x, y, w, h; };
extern int g_8008249c;
extern int g_8008240c;
extern void SetDrawMode(void *p, int dfe, int dtd, int tpage, void *tw);
extern void AddPrim(void *ot, void *prim);

void queue_draw_prim(void)
{
    struct rect26 tw;
    int tpage;
    int cur = g_8008249c;

    tw.x = 0;
    tw.y = 0;
    tw.w = 256;
    tw.h = 256;
    __asm__("lh %0,1292($28)" : "=r"(tpage) : "r"(cur));
    SetDrawMode((void *)cur, 1, 1, tpage, &tw);
    AddPrim((void *)(g_8008240c + 440), (void *)g_8008249c);
    g_8008249c += 12;
}

/* LoadImage @ 0x800628c0 - validate a rect then dispatch a VRAM upload via the GPU driver. */
extern void sub_80062668(void *s, void *rect);
extern void **g_8007fbc0;
extern char g_8001c038[];
void LoadImage(void *rect, void *data)
{
    void **drv;

    sub_80062668(g_8001c038, rect);
    drv = g_8007fbc0;
    ((void (*)(void *, void *, int, void *))drv[2])(drv[8], rect, 8, data);
}

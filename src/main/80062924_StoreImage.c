/* StoreImage @ 0x80062924 - validate a rect then dispatch a VRAM download via the GPU driver. */
extern void sub_80062668(void *s, void *rect);
extern void **g_8007fbc0;
extern char g_8001c044[];
void StoreImage(void *rect, void *data)
{
    void **drv;

    sub_80062668(g_8001c044, rect);
    drv = g_8007fbc0;
    ((void (*)(void *, void *, int, void *))drv[2])(drv[7], rect, 8, data);
}

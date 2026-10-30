/* vram_clear_framebuffers @ 0x80039780 - clear the four VRAM border strips of the
 * double-buffered 1024x512 framebuffer to black, then flush. */
typedef struct { short x, y, w, h; } RECT;
extern void sub_80062790(RECT *r, int a, int b, int c);
extern void sub_800625fc(int a);

void vram_clear_framebuffers(void)
{
    RECT r;

    r.x = 0;    r.y = 0;   r.w = 1023; r.h = 511; sub_80062790(&r, 0, 0, 0);
    r.x = 0;    r.y = 511; r.w = 1023; r.h = 1;   sub_80062790(&r, 0, 0, 0);
    r.x = 1023; r.y = 0;   r.w = 1;    r.h = 511; sub_80062790(&r, 0, 0, 0);
    r.x = 1023; r.y = 511; r.w = 1;    r.h = 1;   sub_80062790(&r, 0, 0, 0);
    sub_800625fc(0);
}

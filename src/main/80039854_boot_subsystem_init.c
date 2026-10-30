/* boot_subsystem_init @ 0x80039854 - boot-time GPU/display bring-up: reset the
 * graphics core (sub_800600cc), set the 256x120 display mode pair
 * (sub_80060614(0x100, 0x78)) and horizontal start (sub_80060634(0xA0)), clear
 * the four border strips of the 1024x512 VRAM double buffer to black via the
 * rect-fill sub_80062790 (same idiom as vram_clear_framebuffers @0x80039780),
 * flush (sub_800625fc(0)), run sub_80039478, then install the VSync callback
 * sub_800390f0 (via sub_80065464) and the CD ready callback sub_80046828 (via
 * sub_8006d8d0) before enabling the display (sub_80062560(1)). */
typedef struct { short x, y, w, h; } RECT;
typedef void (*Callback)(void);

extern int sub_800600cc(void);
extern int sub_80060614(int, int);
extern int sub_80060634(int);
extern void sub_80062790(RECT *r, int a, int b, int c);
extern void sub_800625fc(int);
extern int sub_80039478(void);
extern int sub_80065464(Callback);
extern int sub_8006d8d0(Callback);
extern int sub_80062560(int);
extern void sub_800390f0(void);
extern void sub_80046828(void);

void boot_subsystem_init(void)
{
    RECT r;

    sub_800600cc();
    sub_80060614(0x100, 0x78);
    sub_80060634(0xA0);
    r.x = 0;     r.y = 0;     r.w = 0x3FF; r.h = 0x1FF; sub_80062790(&r, 0, 0, 0);
    r.x = 0;     r.y = 0x1FF; r.w = 0x3FF; r.h = 1;     sub_80062790(&r, 0, 0, 0);
    r.x = 0x3FF; r.y = 0;     r.w = 1;     r.h = 0x1FF; sub_80062790(&r, 0, 0, 0);
    r.x = 0x3FF; r.y = 0x1FF; r.w = 1;     r.h = 1;     sub_80062790(&r, 0, 0, 0);
    sub_800625fc(0);
    sub_80039478();
    sub_80065464(sub_800390f0);
    sub_8006d8d0(sub_80046828);
    sub_80062560(1);
}

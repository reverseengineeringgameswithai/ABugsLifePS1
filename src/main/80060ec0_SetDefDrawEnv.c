/* SetDefDrawEnv @ 0x80060EC0 - libgpu: fill a DRAWENV with defaults for the given
 * clip rect. Layout derived from this binary's stores (clean-room minimal struct,
 * no Sony header): clip x/y/w at +0/+2/+4, clip h at +6, draw offset at +8/+A,
 * tw rect zeroed at +C..+12, tpage=0xA at +14, dtd=1 at +16, isbg/r0/g0/b0
 * zeroed at +18..+1B. dfe (+17) enables drawing-on-display when the clip height
 * fits the video mode's screen (< 0x121 PAL per sub_80065edc()!=0, else < 0x101).
 * Byte-exact needs the if/else arms each storing dfe (cross-jump merges the
 * store) and the tail stores going through the returned temp. */
typedef struct {
    short clip_x, clip_y, clip_w, clip_h;   /* +0..+7 */
    short ofs_x, ofs_y;                     /* +8, +A */
    short tw_x, tw_y, tw_w, tw_h;           /* +C..+12 */
    short tpage;                            /* +14 */
    char dtd, dfe, isbg;                    /* +16, +17, +18 */
    char r0, g0, b0;                        /* +19, +1A, +1B */
} DrawEnvHdr;

extern int sub_80065edc(void);

DrawEnvHdr *SetDefDrawEnv(DrawEnvHdr *env, short x, short y, short w, int h)
{
    int mode;
    DrawEnvHdr *r;

    mode = sub_80065edc();
    env->clip_x = x;
    env->clip_y = y;
    env->clip_w = w;
    env->tw_x = 0;
    env->tw_y = 0;
    env->tw_w = 0;
    env->tw_h = 0;
    env->r0 = 0;
    env->g0 = 0;
    env->b0 = 0;
    env->dtd = 1;
    env->clip_h = (short) h;
    if (mode != 0) {
        env->dfe = h < 0x121;
    } else {
        env->dfe = h < 0x101;
    }
    r = env;
    r->ofs_x = x;
    r->ofs_y = y;
    r->tpage = 0xA;
    r->isbg = 0;
    return r;
}

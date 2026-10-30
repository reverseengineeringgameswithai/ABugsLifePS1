/* vsync_wait_glue @ 0x8003e83c (gp) — pad subsystem (re)start: clear the run
 * flag, settle two frames, re-init direct pad comms with its two buffers, start
 * comms, drain six VSync waits, then mark the subsystem ready. */
extern int  g_80082250[3];    /* absolute (kept out of small data) */
extern short g_8008221c;      /* gp+1156 */
extern char g_800b1fa0[];     /* pad buffer A */
extern char g_800b1fc8[];     /* pad buffer B */
extern void VSync(int);
extern void PadInitDirect(char *, char *);
extern void PadStartCom(void);

void vsync_wait_glue(void)
{
    g_80082250[0] = 0;
    VSync(0);
    VSync(0);
    PadInitDirect(g_800b1fa0, g_800b1fc8);
    PadStartCom();
    VSync(0);
    VSync(0);
    VSync(0);
    VSync(0);
    VSync(0);
    VSync(0);
    g_8008221c = 1;
}

/* vsync_wait_glue_e8c4 @ 0x8003e8c4 (gp) — quiesce the pad subsystem: clear the
 * three run-state flags under a critical section, stop pad comms, then drain
 * several VSync waits. */
extern void EnterCriticalSection(void);
extern int  g_80082250[3];     /* absolute (kept out of small data) */
extern short g_8008221c;       /* gp+1156 */
extern char g_8009e2bc[16];    /* absolute (kept out of small data) */
extern void ExitCriticalSection(void);
extern void VSync(int);
extern void PadStopCom(void);

void vsync_wait_glue_e8c4(void)
{
    EnterCriticalSection();
    g_80082250[0] = 0;
    g_8008221c = 0;
    g_8009e2bc[0] = 0;
    ExitCriticalSection();
    VSync(0);
    VSync(0);
    PadStopCom();
    VSync(0);
    VSync(0);
}

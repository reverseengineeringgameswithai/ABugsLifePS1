/* graphics_reset_teardown - flush/sync GPU then ResetGraph(3). */
extern void DrawSync(int mode);
extern void VSync(int mode);
extern void StopCallback(void);
extern void vsync_wait_glue_e8c4(void);
extern void ResetGraph(int mode);

void graphics_reset_teardown(void)
{
    DrawSync(0);
    DrawSync(0);
    VSync(0);
    VSync(0);
    StopCallback();
    vsync_wait_glue_e8c4();
    ResetGraph(3);
}

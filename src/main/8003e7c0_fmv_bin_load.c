/* fmv_bin_load @ 0x8003e7c0 - load the FMV.BIN MDEC player overlay to Region B
 * (0x800b5788) via the by-name file loader, with pre/post hooks, then enter it. */
extern void sub_80039478(void);
extern void sub_8005b440(void *hook, int b);
extern void sub_80046330(void *name, void *buf);
extern void sub_8005b4e4(void *hook, int b);
extern void sub_800b6250(char *name);
extern void sub_80039854(void);
extern char g_8001ae6c[];   /* "fmv\fmv.bin" */
extern char g_800b5788[];   /* Region B overlay buffer */

void fmv_bin_load(char *name, void *hook)
{
    sub_80039478();
    if (hook != 0)
        sub_8005b440(hook, 0);
    sub_80046330(g_8001ae6c, g_800b5788);
    if (hook != 0)
        sub_8005b4e4(hook, 0);
    sub_800b6250(name);
    sub_80039854();
}

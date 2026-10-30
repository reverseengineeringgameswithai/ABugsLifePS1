/* pad_mode_check @ 0x80073664 - advance the port state machine; returns 1 when settled. */
extern void (*g_80081cf4)(void);
int pad_mode_check(unsigned char *p)
{
    if (p[83] != 0) {
        if (p[70] == 2)
            return 1;
        p[70] = 254;
        return 0;
    }
    g_80081cf4();
    return 0;
}

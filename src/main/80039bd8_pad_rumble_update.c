/* pad_rumble_update - update controller actuator state (small=mode&1, large=mode&0xfe). */
extern unsigned char g_8009e2ba;
extern void PadSetAct(int port, void *act, int len);

void pad_rumble_update(int mode)
{
    unsigned char *p = &g_8009e2ba;

    if (p[0] == (mode & 1) && p[1] == (mode & 0xfe))
        return;

    p[0] = (unsigned char)(mode & 1);
    p[1] = (unsigned char)(mode & 0xfe);
    PadSetAct(0, p, 2);
}

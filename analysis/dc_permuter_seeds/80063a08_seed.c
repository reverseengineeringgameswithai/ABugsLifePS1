extern unsigned char g_8007fbc8;
unsigned int get_mode(int dfe, int dtd, int tpage)
{
    unsigned int cmd, bits;
    if ((unsigned int)(g_8007fbc8 - 1) < 2) {
        cmd = 0xe1000000;
        if (dtd) cmd |= 0x800;
        bits = tpage & 0x27ff;
        if (dfe) bits |= 0x1000;
    } else {
        cmd = 0xe1000000;
        if (dtd) cmd |= 0x200;
        bits = tpage & 0x9ff;
        if (dfe) bits |= 0x400;
    }
    return cmd | bits;
}

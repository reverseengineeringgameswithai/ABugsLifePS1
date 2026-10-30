int pad_direct_engine_ready(unsigned char *p)
{
    if (*(unsigned short *)(p + 230) != 0) {
        if (p[70] == 255) return 0;
    }
    return 1;
}

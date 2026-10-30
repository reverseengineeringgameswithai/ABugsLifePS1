int _padCmdSetMode(unsigned char *p)
{
    int m = p[70];
    int r;
    if (m == 2) { p[55] = 68; *(int *)(p + 44) = (int)(p + 81); p[54] = m; r = 68; }
    else if (m == 3) { p[55] = 3; *(int *)(p + 44) = (int)(p + 93); p[54] = 6; r = 6; }
    else r = 77;
    return r;
}

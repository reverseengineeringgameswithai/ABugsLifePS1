/* _padCmdParaMode @ 0x800736c4 - stage a pad 'C' command with parameter a1. */
void _padCmdParaMode(unsigned char *p, int a1)
{
    p[55] = 67;
    *(unsigned char **)(p + 44) = p + 36;
    p[36] = a1;
    p[54] = 1;
}

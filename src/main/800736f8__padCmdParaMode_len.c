/* _padCmdParaMode variant @ 0x800736f8 - stage a pad 'L' command with parameter. */
void _padCmdParaMode_len(unsigned char *p, int a1)
{
    p[55] = 76;
    *(unsigned char **)(p + 44) = p + 36;
    p[36] = a1;
    p[54] = 1;
}

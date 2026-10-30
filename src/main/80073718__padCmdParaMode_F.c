/* _padCmdParaMode variant @ 0x80073718 - stage a pad command (code 70). */
void _padCmdParaMode_F(unsigned char *p, int a1)
{
    p[55] = 70;
    *(unsigned char **)(p + 44) = p + 36;
    p[36] = a1;
    p[54] = 1;
}

/* _padCmdParaMode variant @ 0x80073738 - stage a pad command (code 71). */
void _padCmdParaMode_G(unsigned char *p, int a1)
{
    p[55] = 71;
    *(unsigned char **)(p + 44) = p + 36;
    p[36] = a1;
    p[54] = 1;
}

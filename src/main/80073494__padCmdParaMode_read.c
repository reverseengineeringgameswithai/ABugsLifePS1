/* _padCmdParaMode variant @ 0x80073494 - stage a pad 'M' read command. */
void _padCmdParaMode_read(unsigned char *p)
{
    int v = *(int *)(p + 32);
    p[55] = 77;
    p[54] = 6;
    *(int *)(p + 44) = v;
}

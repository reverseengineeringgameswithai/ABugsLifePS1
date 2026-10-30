/* FUNC_80072b7c @ 0x80072B7C — sets byte +0x37, word +0x2c, byte +0x36 of the
 * struct in a0 from its args. Matching reimplementation. Fields UNKNOWN.
 *   sb a1,0x37(a0); sw a2,0x2c(a0); jr ra; sb a3,0x36(a0)
 */
void store_three_fields(char *p, int b37, int w2c, int b36)
{
    p[0x37] = b37;
    *(int *)(p + 0x2c) = w2c;
    p[0x36] = b36;
}

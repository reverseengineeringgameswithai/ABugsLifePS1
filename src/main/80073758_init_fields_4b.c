/* FUNC_80073758 @ 0x80073758 — inits struct fields: byte +0x37 = 0x4B,
 * word +0x2c = 0, byte +0x36 = 0. Matching reimplementation. Fields UNKNOWN.
 */
void init_fields_4b(char *p)
{
    p[0x37] = 0x4b;
    *(int *)(p + 0x2c) = 0;
    p[0x36] = 0;
}

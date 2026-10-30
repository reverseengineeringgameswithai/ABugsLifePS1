/* FUNC_800736e4 @ 0x800736E4 — inits struct fields: byte +0x37 = 0x45,
 * word +0x2c = 0, byte +0x36 = 0. Matching reimplementation. Fields UNKNOWN.
 */
void init_fields_45(char *p)
{
    p[0x37] = 0x45;
    *(int *)(p + 0x2c) = 0;
    p[0x36] = 0;
}

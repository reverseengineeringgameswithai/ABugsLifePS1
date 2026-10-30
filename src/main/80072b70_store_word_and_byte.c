/* FUNC_80072b70 @ 0x80072B70 — stores a word at +0x28 and a byte at +0x34 of
 * the struct in a0. Matching reimplementation (docs/SUBSTRATE.md). Purpose of
 * the fields UNKNOWN (byte-match only).
 *   sw a1,0x28(a0); jr ra; sb a2,0x34(a0)
 */
void store_word_and_byte(char *p, int w, int b)
{
    *(int *)(p + 0x28) = w;
    p[0x34] = b;
}

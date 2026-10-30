/* FUNC_80054aac @ 0x80054AAC — stores four byte args to four absolute globals.
 * Matching reimplementation. Global meanings UNKNOWN (address-anchored).
 *   sb a0,0x80082362; sb a1,0x8008248a; sb a2,0x8008241e; sb a3,0x8008248b
 */
extern unsigned char g_80082362, g_8008248a, g_8008241e, g_8008248b;
void store4_bytes(int a0, int a1, int a2, int a3)
{
    g_80082362 = a0;
    g_8008248a = a1;
    g_8008241e = a2;
    g_8008248b = a3;
}

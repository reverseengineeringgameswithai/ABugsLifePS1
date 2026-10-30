/* _getctl @ 0x800645B4 — indexes the libspu control byte table at 0x8008695C by
 * a0 (PsyQ libspu). Matching reimplementation.
 *   lui at,0x8008; addu at,at,a0; lbu v0,0x695c(at); jr ra; nop
 */
extern unsigned char g_8008695c[];
unsigned char _getctl(int i) { return g_8008695c[i]; }

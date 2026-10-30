/* GetIntrMask @ 0x80065538 — reads the current 16-bit interrupt mask through the
 * pointer cached at 0x80080DE8 (I_MASK) (PsyQ libapi). Matching reimplementation.
 * Read side of SetIntrMask.
 *   lui v0,0x8008; lw v0,0xde8(v0); nop; lhu v0,0(v0); jr ra; nop
 */
extern volatile unsigned short *g_80080de8;
unsigned short GetIntrMask(void) { return *g_80080de8; }

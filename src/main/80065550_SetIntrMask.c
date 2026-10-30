/* SetIntrMask @ 0x80065550 — writes a new interrupt mask through the pointer
 * cached at 0x80080DE8 (I_MASK) and returns the previous 16-bit value (PsyQ
 * libapi). Matching reimplementation (docs/SUBSTRATE.md).
 *   lui v1,0x8008; lw v1,0xde8(v1); nop; lhu v0,0(v1); sh a0,0(v1); jr ra
 */
extern volatile unsigned short *g_80080de8;
unsigned short SetIntrMask(short mask)
{
    volatile unsigned short *p = g_80080de8;
    unsigned short old = *p;
    *p = mask;
    return old;
}

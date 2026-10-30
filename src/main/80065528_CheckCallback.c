/* CheckCallback @ 0x80065528 — returns the 16-bit "in callback" flag global at
 * 0x8007FD5A (PsyQ libapi CheckCallback). Matching reimplementation
 * (docs/SUBSTRATE.md). Structural twin of the matched load_global @ 0x80065EDC
 * but a zero-extending halfword load.
 *   lui v0,0x8008; lhu v0,-678(v0); jr ra; nop
 */
extern unsigned short g_8007fd5a;
unsigned short CheckCallback(void)
{
    return g_8007fd5a;
}

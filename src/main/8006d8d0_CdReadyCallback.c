/* CdReadyCallback @ 0x8006D8D0 — installs the CD "data ready" callback pointer
 * (global 0x800818C8) and returns the previous one (PsyQ libcd). Matching
 * reimplementation for the decomp substrate C path (docs/SUBSTRATE.md).
 *   lui v0,0x8008; lw v0,0x18c8(v0); lui at,0x8008; sw a0,0x18c8(at); jr ra
 * Structural twin of the already-matched swap_global @ 0x80065EC4.
 */
extern int g_800818c8;
int CdReadyCallback(int a0)
{
    int v = g_800818c8;
    g_800818c8 = a0;
    return v;
}

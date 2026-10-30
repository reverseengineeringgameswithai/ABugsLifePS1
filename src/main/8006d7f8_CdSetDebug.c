/* CdSetDebug @ 0x8006D7F8 — sets the CD debug-level global (0x800818D0) and
 * returns the previous value (PsyQ libcd). Matching reimplementation
 * (docs/SUBSTRATE.md). Structural twin of CdReadyCallback.
 *   lui v0,0x8008; lw v0,0x18d0(v0); lui at,0x8008; sw a0,0x18d0(at); jr ra
 */
extern int g_800818d0;
int CdSetDebug(int a0)
{
    int v = g_800818d0;
    g_800818d0 = a0;
    return v;
}

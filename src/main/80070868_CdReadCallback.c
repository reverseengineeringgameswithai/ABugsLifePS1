/* CdReadCallback @ 0x80070868 — installs the CD read-done callback pointer
 * (global 0x80081BDC) and returns the previous one (PsyQ libcd). Matching
 * reimplementation. Structural twin of CdReadyCallback.
 *   lui v0,0x8008; lw v0,0x1bdc(v0); lui at,0x8008; sw a0,0x1bdc(at); jr ra
 */
extern int g_80081bdc;
int CdReadCallback(int a0)
{
    int v = g_80081bdc;
    g_80081bdc = a0;
    return v;
}

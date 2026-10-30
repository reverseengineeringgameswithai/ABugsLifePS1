/* CdSyncCallback @ 0x8006D8B8 — installs the CD "sync" callback pointer (global
 * 0x800818C4) and returns the previous one (PsyQ libcd). Matching
 * reimplementation (docs/SUBSTRATE.md). Structural twin of swap_global @ 0x80065EC4.
 *   lui v0,0x8008; lw v0,0x18c4(v0); lui at,0x8008; sw a0,0x18c4(at); jr ra
 */
extern int g_800818c4;
int CdSyncCallback(int a0)
{
    int v = g_800818c4;
    g_800818c4 = a0;
    return v;
}

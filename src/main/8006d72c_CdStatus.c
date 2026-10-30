/* CdStatus @ 0x8006D72C — returns the cached CD status byte (global 0x800818D4)
 * (PsyQ libcd CdStatus). Matching reimplementation (docs/SUBSTRATE.md).
 * Zero-extending byte-load twin of load_global @ 0x80065EDC.
 *   lui v0,0x8008; lbu v0,0x18d4(v0); jr ra; nop
 */
extern unsigned char g_800818d4;
unsigned char CdStatus(void)
{
    return g_800818d4;
}

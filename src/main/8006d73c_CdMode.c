/* CdMode @ 0x8006D73C — returns the cached CD mode byte (global 0x800818E4)
 * (PsyQ libcd). Matching reimplementation (docs/SUBSTRATE.md). Twin of CdStatus.
 *   lui v0,0x8008; lbu v0,0x18e4(v0); jr ra; nop
 */
extern unsigned char g_800818e4;
unsigned char CdMode(void)
{
    return g_800818e4;
}

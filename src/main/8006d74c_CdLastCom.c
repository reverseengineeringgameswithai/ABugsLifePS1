/* CdLastCom @ 0x8006D74C — returns the last CD command byte (global 0x800818E5)
 * (PsyQ libcd). Matching reimplementation. Twin of CdStatus.
 *   lui v0,0x8008; lbu v0,0x18e5(v0); jr ra; nop
 */
extern unsigned char g_800818e5;
unsigned char CdLastCom(void) { return g_800818e5; }

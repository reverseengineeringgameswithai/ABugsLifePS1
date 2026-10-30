/* GetGraphDebug @ 0x800624F4 — returns the libgpu graph-debug byte (global
 * 0x8007FBCA) (PsyQ 4.0.0). Matching reimplementation. Twin of CdStatus.
 *   lui v0,0x8008; lbu v0,-1078(v0); jr ra; nop
 */
extern unsigned char g_8007fbca;
unsigned char GetGraphDebug(void) { return g_8007fbca; }

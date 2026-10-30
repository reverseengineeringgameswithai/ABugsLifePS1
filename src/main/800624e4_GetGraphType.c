/* GetGraphType @ 0x800624E4 — returns the libgpu graph-type byte (global
 * 0x8007FBC8) (PsyQ 4.0.0). Matching reimplementation. Twin of CdStatus.
 *   lui v0,0x8008; lbu v0,-1080(v0); jr ra; nop
 */
extern unsigned char g_8007fbc8;
unsigned char GetGraphType(void) { return g_8007fbc8; }

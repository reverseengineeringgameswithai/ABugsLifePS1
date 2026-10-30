/* FUNC_8006ce6c @ 0x8006CE6C — returns whether the global at 0x800814F8 != 1.
 * Matching reimplementation. Global meaning UNKNOWN.
 *   lw v0,0x14f8(0x8008); xori v0,v0,1; sltu v0,zero,v0; jr ra
 */
extern int g_800814f8;
int global_814f8_ne_1(void) { return g_800814f8 != 1; }

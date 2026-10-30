/* FUNC_800664b8 @ 0x800664B8 — returns the 32-bit global at 0x80080E68.
 * Matching reimplementation. Global meaning UNKNOWN.
 */
extern int g_80080e68;
int load_global_80080e68(void) { return g_80080e68; }

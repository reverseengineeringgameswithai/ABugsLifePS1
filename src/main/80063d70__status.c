/* _status @ 0x80063D70 — double-dereferences the pointer at 0x8007FC9C and
 * returns the 32-bit word it points at (PsyQ libgpu status accessor). Matching
 * reimplementation.
 *   lui v0,0x8008; lw v0,-868(v0); nop; lw v0,0(v0); jr ra; nop
 */
extern int *g_8007fc9c;
int _status(void) { return *g_8007fc9c; }

/* _ctl @ 0x8006458C — writes a libspu control word: stores a0 through the port
 * pointer at 0x8007FC9C and mirrors the low byte into the control-byte table at
 * 0x8008695C indexed by a0>>24 (PsyQ libspu). Matching reimplementation.
 *   lw v0,0x8007fc9c; sw a0,0(v0); srl v0,a0,24; sb a0,0x695c(0x8008+v0)
 */
extern int *g_8007fc9c;
extern unsigned char g_8008695c[];
void _ctl(unsigned int a0)
{
    *g_8007fc9c = a0;
    g_8008695c[a0 >> 24] = a0;
}

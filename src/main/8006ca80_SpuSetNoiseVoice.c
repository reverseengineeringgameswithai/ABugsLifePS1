/* SpuSetNoiseVoice @ 0x8006CA80 — forwards to _SpuSetAnyVoice(a0,a1,0xCA,0xCB)
 * (PsyQ libspu). 1-callee wrapper with fixed trailing args.
 *   a2=0xca; a3=0xcb; jal _SpuSetAnyVoice
 */
extern void _SpuSetAnyVoice(int a0, int a1, int a2, int a3);
void SpuSetNoiseVoice(int a0, int a1)
{
    _SpuSetAnyVoice(a0, a1, 0xca, 0xcb);
}

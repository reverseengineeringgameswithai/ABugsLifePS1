/* SsVabOpenHead @ 0x8006B130 — PsyQ libspu: opens a VAB header, forwarding to
 * SsVabOpenHeadWithMode(vabhdr, (short)vabid, 0, 0) and returning the vabId as a
 * sign-extended short. Documented site in src_re/sfx_system.c (SsVabOpenHead
 * 0x8006B130). 1-callee wrapper; callee resolved by census name (auto-defsym).
 *   a1=(short)a1; a2=0; a3=0; jal SsVabOpenHeadWithMode; v0=(short)v0
 */
extern int SsVabOpenHeadWithMode(int a0, int a1, int a2, int a3);
short SsVabOpenHead(int vabhdr, short vabid)
{
    return SsVabOpenHeadWithMode(vabhdr, vabid, 0, 0);
}

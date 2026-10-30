/* FUNC_80050838 @ 0x80050838 — sfx_menu_blip (menu-cursor blip), from
 * src_re/sfx_system.c. 1-callee wrapper computing an SPU voice/param address:
 * decrements the id, forms ((id-1)&0xf)<<7 + 0x1200, and forwards to
 * FUNC_800435F8(id-1, param, a1, a2). Callee resolved by auto-defsym (sub_).
 *   a0-=1; a1=((a0&0xf)<<7)+0x1200; a2=orig_a1 (delay); jal sub_800435f8
 */
extern int sub_800435f8(int a0, int a1, int a2, int a3);
void sfx_menu_blip(int a0, int a1, int a2)
{
    int d = a0 - 1;
    sub_800435f8(d, ((d & 0xf) << 7) + 0x1200, a1, a2);
}

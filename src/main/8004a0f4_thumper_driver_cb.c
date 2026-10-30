/* FUNC_8004a0f4 @ 0x8004A0F4 — thumper_driver_cb, game code (Thumper boss;
 * Canon: thumper-boss). Per-frame driver callback: invokes sub_8005044c with
 * id 26 and the actor's field-4 pointer advanced by 4.
 *
 * Matching reimplementation (docs/SUBSTRATE.md C path). CLASS: understood named
 * function calling a subroutine (auto-defsym via the sub_<addr> anchor).
 *
 *   lw a1,4(a0); li a0,26; jal 0x8005044c; addiu a1,a1,4
 */
extern void sub_8005044c(int id, int arg);

void thumper_driver_cb(int *actor)
{
    sub_8005044c(26, actor[1] + 4);
}

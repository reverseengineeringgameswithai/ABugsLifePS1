/* FUNC_8002d64c @ 0x8002D64C — thin wrapper, game code.
 * Called from 0x8001db88 / 0x8001e7bc / 0x80021d84; tail-forwards its argument
 * to sub_8002b424 with fixed trailing args (-1, 0, 0) and returns the result.
 *
 * Matching reimplementation (docs/SUBSTRATE.md C path). CLASS PROOF: one callee,
 * demonstrating auto-defsym callee resolution — `sub_8002b424` is resolved to
 * its VA from its address-anchored name, no explicit externs needed.
 *
 * Original:
 *   addiu sp,-24; sw ra,16(sp)
 *   addiu a1,-1; move a2,zero; jal 0x8002b424; move a3,zero
 *   lw ra,16(sp); addiu sp,24; jr ra
 *
 * a0 is passed through unchanged; sub_8002b424's role is UNKNOWN (no evidence).
 */
extern int sub_8002b424(int a0, int a1, int a2, int a3);

int call_8002b424_wrapper(int a0)
{
    return sub_8002b424(a0, -1, 0, 0);
}

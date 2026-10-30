/* empty stub @ 0x800b3b0c (LEVEL02_LEVEL1 overlay, 8 B) — jr ra; nop.
 * A do-nothing overlay routine (unpopulated verb slot). Second overlay BLOB on
 * the track after the LEVEL02_LEVEL proof: exercises the multi-blob build/validate
 * path (compiled at the Region-A load VA, spliced into a copy of the blob).
 *   0x800b3b0c: 03e00008 jr ra ; 0x800b3b10: 00000000 nop
 */
void overlay_stub_800b3b0c(void) {}

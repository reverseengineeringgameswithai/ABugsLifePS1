/* Decomp substrate v0 — link one assembled function at its original VA.
 * Used per-function: ld -T config/linker.ld --defsym __va=0x<start>.
 * (docs/SUBSTRATE.md; the byte-splat build splices the objcopy'd binary
 * into a copy of the original image.) */
OUTPUT_FORMAT("elf32-tradlittlemips")
OUTPUT_ARCH(mips)
SECTIONS
{
  . = DEFINED(__va) ? __va : 0x80010000;
  /* SUBALIGN(4): gas gives even empty .data 2**4 alignment, which would pad
   * the merged section to 16 — MIPS-I code only ever needs 4. */
  /* .rdata* catches cc1's switch jump tables (`.rdata` `.align 3`, `.word $Ln`);
   * with --section-start the R_MIPS_32 table entries resolve to the correct
   * case-label VAs (substrate v2 jr-table mechanism). */
  .out : SUBALIGN(4) { *(.text*) *(.rodata*) *(.rdata*) *(.data*) }
  /DISCARD/ : { *(.reginfo) *(.MIPS.abiflags) *(.gnu.attributes) *(.pdr) *(.comment) *(.mdebug*) }
}

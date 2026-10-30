/* Optional split-section link for C functions whose compiler-emitted switch
 * table belongs in a fixed resident rodata pool rather than after .text. */
OUTPUT_FORMAT("elf32-tradlittlemips")
OUTPUT_ARCH(mips)
SECTIONS
{
  .textout (DEFINED(__text_va) ? __text_va : 0x80010000) : SUBALIGN(4) {
    *(.text*)
  }
  .rdataout (DEFINED(__rdata_va) ? __rdata_va : 0x80080000) : SUBALIGN(4) {
    *(.rodata*) *(.rdata*)
  }
  .dataout (DEFINED(__data_va) ? __data_va : 0x80081000) : SUBALIGN(4) {
    *(.data*)
  }
  /DISCARD/ : { *(.reginfo) *(.MIPS.abiflags) *(.gnu.attributes) *(.pdr) *(.comment) *(.mdebug*) }
}

/* CdFlush @ 0x8006d7d8 - forward to the low-level flush routine. */
extern void sub_8006ee30(void);
void CdFlush(void) { sub_8006ee30(); }

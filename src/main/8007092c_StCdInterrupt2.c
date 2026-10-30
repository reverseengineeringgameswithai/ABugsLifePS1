/* StCdInterrupt2 @ 0x8007092c - forward to the streaming CD interrupt handler. */
extern void sub_80070d80(void);
void StCdInterrupt2(void) { sub_80070d80(); }

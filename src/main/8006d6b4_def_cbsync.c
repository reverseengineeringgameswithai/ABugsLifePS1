/* def_cbsync @ 0x8006d6b4 - register the default CdRom def_cbsync callback (event 0xf0000003). */
extern void sub_8006c3ac(int event, int mask);
void def_cbsync(void) { sub_8006c3ac(0xf0000003, 32); }

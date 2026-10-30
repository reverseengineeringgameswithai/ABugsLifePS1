/* def_cbready @ 0x8006d6dc - register the default CdRom def_cbready callback (event 0xf0000003). */
extern void sub_8006c3ac(int event, int mask);
void def_cbready(void) { sub_8006c3ac(0xf0000003, 64); }

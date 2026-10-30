/* def_cbread @ 0x8006d704 - register the default CdRom def_cbread callback (event 0xf0000003). */
extern void sub_8006c3ac(int event, int mask);
void def_cbread(void) { sub_8006c3ac(0xf0000003, 64); }

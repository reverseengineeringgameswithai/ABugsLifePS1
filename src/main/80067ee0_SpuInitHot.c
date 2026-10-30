/* SpuInitHot @ 0x80067ee0 - initialize the SPU in "hot"/re-init mode. */
extern void sub_80067c78(int mode);
void SpuInitHot(void) { sub_80067c78(1); }

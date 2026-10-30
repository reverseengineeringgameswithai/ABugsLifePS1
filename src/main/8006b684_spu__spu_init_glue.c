/* spu__spu_init_glue @ 0x8006B684 — calls _SpuInit(0). */
extern void _SpuInit(int);
void spu_init_glue(void) { _SpuInit(0); }

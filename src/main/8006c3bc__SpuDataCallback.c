/* _SpuDataCallback @ 0x8006c3bc - register SPU DMA-complete callback (event 4). */
extern void sub_80065434(int event, int cb);
void _SpuDataCallback(int cb) { sub_80065434(4, cb); }

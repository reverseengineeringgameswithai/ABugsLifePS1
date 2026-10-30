/* sound library init: ResetCallback, SPU init glue, _SsInit. */
extern void ResetCallback(void);
extern void spu__spu_init_glue(void);
extern void _SsInit(void);

void sound_lib_init_sequence(void)
{
    ResetCallback();
    spu__spu_init_glue();
    _SsInit();
}

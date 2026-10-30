/* call_vptr56_sign - dispatch fnptr at obj+56 ($v0-input tail); return sign bit. */
int call_vptr56_sign(void)
{
    register char *obj asm("$2");
    return (unsigned int)(*(int (**)(void))(obj + 56))() >> 31;
}

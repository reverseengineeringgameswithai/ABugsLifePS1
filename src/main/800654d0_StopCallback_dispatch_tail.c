/* StopCallback_dispatch_tail - dispatch fnptr at obj+16 ($v0-input tail). */
void StopCallback_dispatch_tail(void)
{
    register char *cb asm("$2");
    (*(void (**)(void))(cb + 16))();
}

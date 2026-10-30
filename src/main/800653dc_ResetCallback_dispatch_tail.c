/* ResetCallback_dispatch_tail - tail-call fnptr at +0xC of the incoming $v0 object. */
void ResetCallback_dispatch_tail(void)
{
    register char *self asm("$2");
    (*(void (**)(void))(self + 12))();
}

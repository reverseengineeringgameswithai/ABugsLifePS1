/* VSyncCallbacks_dispatch_tail - $v0-input tail; call fnptr at +0x14. */
struct cb_obj { char pad[20]; void (*fn)(void); };

void VSyncCallbacks_dispatch_tail(void)
{
    register struct cb_obj *p asm("$2");
    p->fn();
}

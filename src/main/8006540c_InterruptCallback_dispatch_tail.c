/* InterruptCallback_dispatch_tail - dispatch through vtable slot +8; base arrives in $v0 (non-ABI tail). */
struct cb { void (*slot0)(void); void (*slot4)(void); void (*slot8)(void); };

void InterruptCallback_dispatch_tail(void)
{
    register struct cb *cb asm("$2");
    cb->slot8();
}

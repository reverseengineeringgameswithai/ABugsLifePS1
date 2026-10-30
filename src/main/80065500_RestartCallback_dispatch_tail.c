/* RestartCallback_dispatch_tail - dispatch through vtable slot +24; base arrives in $v0. */
void RestartCallback_dispatch_tail(void)
{
    register char *cb asm("$2");
    (*(void (**)(void))(cb + 24))();
}

/* exec_queue_kick - object ptr in $v0; call fnptr at +4. */
void exec_queue_kick(void)
{
    register char *obj asm("$2");
    void (*fn)(void) = *(void (**)(void))(obj + 4);

    fn();
}

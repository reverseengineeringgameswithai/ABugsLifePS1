/* pad_subsystem_shutdown - stop pad driver, StopPAD2, dequeue IRQ handler, clear ready flag. */
extern void pad_stop_driver_thunk(void);
extern void StopPAD2(void);
extern void interrupt_handler_dequeue(void);
extern int g_80080e68;

void pad_subsystem_shutdown(void)
{
    pad_stop_driver_thunk();
    StopPAD2();
    interrupt_handler_dequeue();
    g_80080e68 = 0;
}

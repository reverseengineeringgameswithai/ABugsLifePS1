/* interrupt_handler_dequeue @ 0x800666c8 */
extern void EnterCriticalSection(void);
extern int  SysDeqIntRP(int priority, void *cb);
extern void ExitCriticalSection(void);
extern int  g_80086a90[4];

int interrupt_handler_dequeue(void) {
    EnterCriticalSection();
    SysDeqIntRP(1, g_80086a90);
    ExitCriticalSection();
    return 1;
}

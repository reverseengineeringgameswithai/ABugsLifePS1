/* event_open_enable - $v0=already-done flag; register SPU DMA callback + open/enable event in crit section. */
extern int EnterCriticalSection(void);
extern void ExitCriticalSection(void);
extern void _spu_FiDMA(void);
extern void _SpuDataCallback(void *cb);
extern int OpenEvent(unsigned int cls, int spec, int mode, void *func);
extern void EnableEvent(int event);
extern int g_800814c0;
extern int g_80081058;

void event_open_enable(void)
{
    register int already asm("$2");
    int ev;
    if (already)
        return;
    g_800814c0 = 1;
    EnterCriticalSection();
    _SpuDataCallback((void *)_spu_FiDMA);
    ev = OpenEvent(0xf0000009u, 32, 8192, 0);
    g_80081058 = ev;
    EnableEvent(ev);
    ExitCriticalSection();
}

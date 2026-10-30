/* CdRead2 @ 0x80070898 (148 B) — libcd streamed-read starter (CdlReadS path).
 * Sets the CD mode (command 0x0e) with the caller's mode byte; when mode bit
 * 0x100 is set, selects the double-buffer flag g_80090744 from mode bit 0x20
 * (clear -> 1, set -> 0) and installs the data-ready + complete callbacks; then
 * issues CdlReadS (command 0x1b) and returns its submit result.
 * SDK (libcd); reconstructed clean-room from the disasm at 0x80070898.
 *   func_8006d8e8 = CdControlB(com, param, result); func_8006dcf0 / func_8006d8d0
 *   install the ready/complete callbacks (func_80070a30 / func_8007092c). */

extern int  func_8006d8e8(int com, void *param, int result);
extern void func_8006dcf0(void *cb);
extern void func_8006d8d0(void *cb);
extern void func_8007092c(void);
extern void func_80070a30(void);
extern int  g_80090744;

int CdRead2(int mode)
{
    unsigned char m = (unsigned char)mode;

    func_8006d8e8(0xe, &m, 0);
    if (mode & 0x100) {
        if (mode & 0x20)
            g_80090744 = 0;
        else
            g_80090744 = 1;
        func_8006dcf0((void *)func_80070a30);
        func_8006d8d0((void *)func_8007092c);
    }
    return func_8006d8e8(0x1b, 0, 0);
}

/* CdInit @ 0x8006D61C - libcd: reset the CD subsystem with up to 5 attempts of
 * sub_8006d76c(1); on success install the three default completion callbacks
 * (sub_8006d6b4 / sub_8006d6dc / sub_8006d704, the functions directly after this
 * one) via their setters and clear the pending state (sub_80070880(0)), else
 * report the failure string g_8001c2c0 through sub_8005f7dc and return 0.
 * Byte-exact needs the goto retry loop (a structured loop hoists the comparison
 * constants into saved regs; retail rematerializes them) and the if/else with a
 * single return joining at a common epilogue. */
typedef void (*Callback)(void);

extern char g_8001c2c0[];
extern int sub_8006d76c(int);
extern int sub_8006d8b8(Callback);
extern int sub_8006d8d0(Callback);
extern int sub_80070868(Callback);
extern int sub_80070880(int);
extern int sub_8005f7dc(void *);
extern void sub_8006d6b4(void);
extern void sub_8006d6dc(void);
extern void sub_8006d704(void);

int CdInit(void)
{
    int n;
    int ret;

    n = 4;
retry:
    if (sub_8006d76c(1) == 1) {
        sub_8006d8b8(sub_8006d6b4);
        sub_8006d8d0(sub_8006d6dc);
        sub_80070868(sub_8006d704);
        sub_80070880(0);
        ret = 1;
    } else {
        n = n - 1;
        if (n != -1)
            goto retry;
        sub_8005f7dc(g_8001c2c0);
        ret = 0;
    }
    return ret;
}

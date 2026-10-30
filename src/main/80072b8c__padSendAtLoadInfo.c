/* _padSendAtLoadInfo @ 0x80072b8c - dispatch the port's per-mode actuator-load
 * command. `switch` matches the original jump-free 4-way branch codegen. */
extern void sub_800736e4(unsigned char *p);
extern void sub_800736f8(unsigned char *p, int a);
extern void sub_80073738(unsigned char *p, int a);
void _padSendAtLoadInfo(unsigned char *p)
{
    switch (p[70]) {
        case 2: sub_800736e4(p); break;
        case 3: sub_800736f8(p, p[228]); break;
        case 4: sub_80073738(p, p[71]); break;
    }
}

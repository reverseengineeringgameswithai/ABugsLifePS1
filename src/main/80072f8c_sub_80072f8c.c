/* sub_80072f8c @ 0x80072f8c - dispatch the port's per-mode command by the byte
 * at p[70] (structural sibling of _padSendAtLoadInfo). switch matches the
 * jump-free multi-branch codegen; m2c-seeded (dc-9), signature hand-finished. */
extern int sub_800736f8(unsigned char *p, int a);
extern int sub_80073718(unsigned char *p, int a);
extern int sub_80073738(unsigned char *p, int a);
extern int sub_80073758(unsigned char *p);
void sub_80072f8c(unsigned char *p)
{
    switch (p[70]) {
        case 2: sub_800736f8(p, p[71]); return;
        case 3: sub_80073718(p, p[71]); return;
        case 4:
            if (p[72] == 0) { sub_80073738(p, p[71]); return; }
            sub_80073758(p); return;
    }
}

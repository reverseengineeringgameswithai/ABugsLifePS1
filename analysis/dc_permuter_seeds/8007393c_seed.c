extern int (*g_80081cf8)(unsigned char *, int);
extern int sub_80072834(unsigned char *, int);

int pad_sio_stage_transfer(unsigned char *p)
{
    int flag = 0;
    int r1, r, v;
    if ((*(unsigned char *)(((int *)p)[15]) >> 4) == 8)
        flag = p[55] < 1;
    r1 = (*g_80081cf8)(p, flag);
    r = sub_80072834(p, r1 & 0xff);
    v = r;
    if (r == 90) goto out;
    if (r == 0) goto out;
    if (r >= 0) v = -4;
out:
    return v;
}

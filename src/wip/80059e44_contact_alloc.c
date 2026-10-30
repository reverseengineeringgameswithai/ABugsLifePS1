/* contact_alloc (spawn_drop) @ 0x80059e44 (668 B) — allocate + construct a contact record.
 * Behavior from src_re/contact_alloc_80059e44.c (CONFIRMED). ABI:
 *   rec = contact_alloc(x, y, z, ctorType=a3, stackArg=[sp+0x40]).
 * Advance the 64-entry allocator cursor (wrap at 0x40), skip occupied slots
 * (flags bit7 set AND active_type != 0), then fill the 0x38-byte record from the
 * coords, render-attr table A (index stackArg, via func_800593e8 per A[0] nibble),
 * and metadata table B (index ctorType). Absolute-addressed globals (-G0). */

extern int  contact_scatter_component_decode(int selector, int value);
extern void func_80024ddc(void *rec);

extern int            g_8008234c;      /* alloc cursor (wrap 0x40)        */
extern unsigned char  g_800b0d18[];    /* contact array, 0x38 stride      */
extern unsigned char  g_8007941c[];    /* metadata B, 0x14 stride (ctorType) */
extern unsigned char  g_80079e30[];    /* metadata A, 0x14 stride (stackArg) */
extern unsigned char *g_800822f4;      /* script cursor (metaB+4 < 0 path) */

void *contact_alloc(int x, int y, int z, int ctorType, int stackArg)
{
    unsigned char *rec, *A, *B;
    int slot, c;
    short m4;

    for (;;) {
        c = g_8008234c + 1;
        g_8008234c = c;
        if (c >= 0x40)
            g_8008234c = 0;
        slot = g_8008234c;
        if (!(g_800b0d18[slot * 0x38 + 0x33] & 0x80))
            break;
        if (*(short *)&g_800b0d18[slot * 0x38 + 0x22] == 0)
            break;
    }

    rec = &g_800b0d18[slot * 0x38];
    A = &g_80079e30[stackArg * 0x14];
    B = &g_8007941c[ctorType * 0x14];

    *(int *)(rec + 0x00) = x;
    *(int *)(rec + 0x04) = y;
    *(int *)(rec + 0x08) = z;

    *(int *)(rec + 0x0c) = contact_scatter_component_decode((*(int *)A & 0xf000) >> 12, *(int *)(A + 0x04));
    *(int *)(rec + 0x10) = contact_scatter_component_decode((*(int *)A & 0x0f00) >>  8, *(int *)(A + 0x08));
    *(int *)(rec + 0x14) = contact_scatter_component_decode((*(int *)A & 0x00f0) >>  4, *(int *)(A + 0x0c));
    *(int *)(rec + 0x18) = contact_scatter_component_decode((*(int *)A & 0x000f)      , *(int *)(A + 0x10));

    *(int *)(rec + 0x1c) = -1;
    rec[0x32] = 0x20;
    rec[0x33] = B[0x10];
    *(short *)(rec + 0x20) = *(unsigned short *)(B + 0x00);
    *(short *)(rec + 0x22) = *(unsigned short *)(B + 0x02);
    rec[0x30] = B[0x07];
    rec[0x31] = B[0x06];

    m4 = *(short *)(B + 0x04);
    if (m4 >= 0) {
        *(short *)(rec + 0x24) = m4;
    } else {
        unsigned char *cur = g_800822f4;
        int d;
        g_800822f4 = cur + 1;
        d = (*cur & 3) - *(unsigned short *)(B + 0x04);
        *(short *)(rec + 0x24) = (short)d;
        *(short *)(rec + 0x22) = (short)((short)d * rec[0x30]);
    }
    *(short *)(rec + 0x26) = *(unsigned short *)(rec + 0x24);

    rec[0x34] = B[0x11];
    rec[0x35] = B[0x12];
    rec[0x36] = B[0x13];
    *(short *)(rec + 0x28) = *(unsigned short *)(B + 0x08);
    *(short *)(rec + 0x2a) = *(unsigned short *)(B + 0x0a);
    *(short *)(rec + 0x2c) = *(unsigned short *)(B + 0x0c);
    rec[0x2f] = B[0x0f];

    {
        signed char sel = (signed char)B[0x0e];
        if (sel == 0)
            rec[0x2e] = 0;
        else if (sel == 1)
            rec[0x2e] = (unsigned char)ctorType;
        else
            rec[0x2e] = (unsigned char)(-ctorType);
    }

    func_80024ddc(rec);
    return rec;
}

/* SetLineF4 @ 0x80061E0C — libgpu LINE_F4 primitive initializer (PsyQ 4.0.0). Twin of
 * SetPolyGT4 (len@+3, code@+7) plus the 0x55555555 line-strip terminator word
 * written at +0x18. Clean-room minimal tag struct (no Sony header).
 *   lui/ori v1,0x55555555; addiu v0,6; sb v0,3(a0); addiu v0,0x4c; sb v0,7(a0);
 *   jr ra; sw v1,24(a0)
 */
typedef struct {
    unsigned char pad0, pad1, pad2, len;    /* +0..+3 */
    unsigned char pad4, pad5, pad6, code;   /* +4..+7 */
    unsigned char body[16];          /* vertices up to the terminator */
    unsigned int  term;                     /* +0x18: 0x55555555 pad word */
} LINE_F4;

void SetLineF4(LINE_F4 *p)
{
    p->len = 6;
    p->code = 0x4c;
    p->term = 0x55555555;
}

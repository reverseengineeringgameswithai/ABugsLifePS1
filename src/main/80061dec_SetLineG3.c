/* SetLineG3 @ 0x80061DEC — libgpu LINE_G3 primitive initializer (PsyQ 4.0.0). Twin of
 * SetPolyGT4 (len@+3, code@+7) plus the 0x55555555 line-strip terminator word
 * written at +0x1c. Clean-room minimal tag struct (no Sony header).
 *   lui/ori v1,0x55555555; addiu v0,7; sb v0,3(a0); addiu v0,0x58; sb v0,7(a0);
 *   jr ra; sw v1,28(a0)
 */
typedef struct {
    unsigned char pad0, pad1, pad2, len;    /* +0..+3 */
    unsigned char pad4, pad5, pad6, code;   /* +4..+7 */
    unsigned char body[20];          /* vertices up to the terminator */
    unsigned int  term;                     /* +0x1c: 0x55555555 pad word */
} LINE_G3;

void SetLineG3(LINE_G3 *p)
{
    p->len = 7;
    p->code = 0x58;
    p->term = 0x55555555;
}

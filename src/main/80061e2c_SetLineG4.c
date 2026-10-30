/* SetLineG4 @ 0x80061E2C — libgpu LINE_G4 primitive initializer (PsyQ 4.0.0). Twin of
 * SetPolyGT4 (len@+3, code@+7) plus the 0x55555555 line-strip terminator word
 * written at +0x24. Clean-room minimal tag struct (no Sony header).
 *   lui/ori v1,0x55555555; addiu v0,9; sb v0,3(a0); addiu v0,0x5c; sb v0,7(a0);
 *   jr ra; sw v1,36(a0)
 */
typedef struct {
    unsigned char pad0, pad1, pad2, len;    /* +0..+3 */
    unsigned char pad4, pad5, pad6, code;   /* +4..+7 */
    unsigned char body[28];          /* vertices up to the terminator */
    unsigned int  term;                     /* +0x24: 0x55555555 pad word */
} LINE_G4;

void SetLineG4(LINE_G4 *p)
{
    p->len = 9;
    p->code = 0x5c;
    p->term = 0x55555555;
}

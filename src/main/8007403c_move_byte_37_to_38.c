/* FUNC_8007403c @ 0x8007403C — moves the byte at +0x37 to +0x38 and clears
 * +0x37. Matching reimplementation. Field meanings UNKNOWN.
 *   lbu v0,0x37(a0); sb zero,0x37(a0); jr ra; sb v0,0x38(a0)
 */
void move_byte_37_to_38(unsigned char *p)
{
    unsigned char x = p[0x37];
    p[0x37] = 0;
    p[0x38] = x;
}

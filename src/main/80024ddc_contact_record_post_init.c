/* FUNC_80024ddc @ 0x80024DDC — contact-record post-init, game code.
 * Sets the record's state byte (+0x37): default 0x2c, or 0x2e unless the
 * flag byte (+0x33) has both bits 0x60 set. (Canon: state byte +0x37.)
 *
 * Matching reimplementation (docs/SUBSTRATE.md C path). CLASS PROOF: control
 * flow — a branch with a delay slot + signed/unsigned byte fields. Leaf.
 *
 * Original:
 *   lbu v0,0x33(a0); li v1,0x2c; sb v1,0x37(a0)
 *   li v1,0x60; andi v0,v0,0x60; beq v0,v1,ret; li v0,0x2e; sb v0,0x37(a0); ret
 *
 * The 0x2c/0x2e state values and the 0x60 mask are as-shipped; their meaning
 * beyond "state byte" is not further evidenced here.
 */
void contact_record_post_init(unsigned char *rec)
{
    rec[0x37] = 0x2c;
    if ((rec[0x33] & 0x60) != 0x60) {
        rec[0x37] = 0x2e;
    }
}

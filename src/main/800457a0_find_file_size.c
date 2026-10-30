/* FUNC_800457a0 @ 0x800457A0 — CD file-size lookup, game code.
 * Retries CdSearchFile (0x8006F690) until it succeeds, then returns the found
 * file's size field.
 *
 * Matching reimplementation (docs/SUBSTRATE.md C path). CLASS PROOF: a saved
 * callee-saved register (s0) + a stack-local struct + a retry loop + a callee.
 * This function DISCRIMINATES the optimization level: it matches at -O2 and
 * DIFFERS at -O1 (3 words) — evidence that game code was built -O2.
 *
 * Original:
 *   addiu sp,-48; sw s0,40(sp); move s0,a0; sw ra,44(sp)
 *   L: addiu a0,sp,16; jal 0x8006f690; move a1,s0; beqz v0,L; addiu a0,sp,16
 *   lw v0,20(sp); lw ra,44(sp); lw s0,40(sp); addiu sp,48; jr ra
 *
 * The local's size field is at +4; the struct's exact PsyQ identity/other
 * fields are not evidenced here (clean-room 24-byte layout that reproduces the
 * frame the compiler emitted).
 */
struct cdfile { int pos; int size; int pad[4]; };   /* 24 bytes: size at +4 */

extern int CdSearchFile(struct cdfile *fp, char *name);   /* 0x8006F690 */

int find_file_size(char *name)
{
    struct cdfile fp;
    while (CdSearchFile(&fp, name) == 0) ;
    return fp.size;
}

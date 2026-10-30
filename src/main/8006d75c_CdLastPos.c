/* CdLastPos @ 0x8006D75C — returns the address of the cached last-position
 * struct (global 0x800818E0) (PsyQ libcd). Matching reimplementation
 * (docs/SUBSTRATE.md). Address-of a global (la idiom).
 *   lui v0,0x8008; addiu v0,v0,0x18e0; jr ra; nop
 */
extern unsigned char g_800818e0;
void *CdLastPos(void)
{
    return &g_800818e0;
}
